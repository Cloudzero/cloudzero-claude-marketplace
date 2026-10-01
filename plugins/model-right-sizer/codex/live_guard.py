# SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Active app-server budget polling and exact turn/steer warning delivery.

Connect this controller to the host's main-agent transport; it does not require
an economist agent. Both billing polls and native token-usage notifications are
observations, not an invented ticker. RPC acknowledgement proves delivery to
the active turn; actual final spend and the work trace evaluate the outcome.
"""
from datetime import datetime, timezone
import math
import time

try:
    from runtime import CORE
except ImportError:
    from right_sizer import CORE
import sys
sys.path.insert(0, str(CORE / 'eval'))
from budget_threshold import threshold_crossed, format_budget_warning


def timestamp():
    return datetime.now(timezone.utc).isoformat()


class BudgetPoller:
    def __init__(self, unit_id, thread_id, turn_id, ceiling, threshold=.7, poll_interval=2, poll_timeout=10, baseline_tokens=0):
        if isinstance(ceiling, bool) or not isinstance(ceiling, int) or ceiling < 0:
            raise ValueError('Ceiling must be a nonnegative integer')
        if isinstance(baseline_tokens, bool) or not isinstance(baseline_tokens, int) or baseline_tokens < 0:
            raise ValueError('Unit baseline must be a measured nonnegative integer')
        threshold_crossed(0, ceiling, threshold)
        format_budget_warning(unit_id, 0, ceiling, threshold)
        if not isinstance(poll_interval, (int,float)) or not math.isfinite(poll_interval) or poll_interval < .25:
            raise ValueError('Polling interval must be finite and at least 0.25 seconds')
        if isinstance(poll_timeout, bool) or not isinstance(poll_timeout, (int,float)) or not math.isfinite(poll_timeout) or poll_timeout < poll_interval:
            raise ValueError('Polling timeout must be finite and at least the polling interval')
        self.unit_id, self.thread_id, self.turn_id = unit_id, thread_id, turn_id
        self.ceiling, self.threshold, self.poll_interval = ceiling, threshold, poll_interval
        self.actual_tokens = None
        self.events = []
        self.pending_polls = set()
        self.pending_steer = None
        self.warning_delivered = False
        self.finished = False
        self.last_poll_at = None
        self.crossing_total = None
        self.poll_timeout = poll_timeout
        self.pending_poll_sent_at = None
        self.baseline_tokens = baseline_tokens

    def tick(self, rpc, clock=None):
        clock = time.monotonic() if clock is None else clock
        if self.finished:
            return
        if self.pending_polls and clock-self.pending_poll_sent_at >= self.poll_timeout:
            self.events.append({'type':'poll_timed_out','at':timestamp()})
            self.pending_polls.clear()
            self.pending_poll_sent_at = None
        if self.last_poll_at is None or clock-self.last_poll_at >= self.poll_interval:
            # Never pile up unanswered requests on a slow billing endpoint.
            if not self.pending_polls:
                ident = rpc.send('account/usage/read', {'threadId': self.thread_id})
                self.pending_polls.add(ident)
                self.pending_poll_sent_at = clock
                self.events.append({'type':'poll_sent','at':timestamp(),'request_id':ident})
            self.last_poll_at = clock

    def observe(self, tokens, source, rpc):
        if isinstance(tokens, bool) or not isinstance(tokens, int) or tokens < 0:
            raise ValueError('Only measured nonnegative integer usage is accepted')
        if tokens < self.baseline_tokens:
            self.events.append({'type':'snapshot_before_baseline','at':timestamp(),'source':source,'tokens':tokens})
            return
        tokens -= self.baseline_tokens
        if self.actual_tokens is not None and tokens < self.actual_tokens:
            self.events.append({'type':'stale_snapshot','at':timestamp(),'source':source,'tokens':tokens})
            return
        self.actual_tokens = tokens
        self.events.append({'type':'usage_observed','at':timestamp(),'source':source,'tokens':tokens})
        if not threshold_crossed(tokens, self.ceiling, self.threshold):
            return
        if self.crossing_total is None:
            self.crossing_total = tokens
        if self.finished or self.warning_delivered or self.pending_steer is not None:
            return
        warning = format_budget_warning(self.unit_id, tokens, self.ceiling, self.threshold)
        self.pending_steer = rpc.send('turn/steer', {'threadId':self.thread_id,
            'expectedTurnId':self.turn_id,'input':[{'type':'text','text':warning}]})
        self.events.append({'type':'warning_sent','at':timestamp(),'request_id':self.pending_steer,'message':warning})

    def handle(self, message, rpc):
        ident = message.get('id')
        if ident in self.pending_polls:
            self.pending_polls.remove(ident)
            self.pending_poll_sent_at = None
            if 'error' in message:
                self.events.append({'type':'poll_rejected','at':timestamp(),
                                    'message':message['error'].get('message')})
            else:
                usage = message['result'].get('threadUsage')
                groups = usage.get('groups') if usage and usage.get('threadId') == self.thread_id else None
                if groups and all(isinstance(g.get('totalTokens'),int) and not isinstance(g.get('totalTokens'),bool)
                                  and g['totalTokens'] >= 0 for g in groups):
                    self.observe(sum(g['totalTokens'] for g in groups), 'account_usage_poll', rpc)
                else:
                    self.events.append({'type':'poll_usage_unknown','at':timestamp()})
            return
        if ident is not None and ident == self.pending_steer:
            if 'result' in message and message['result'].get('turnId') == self.turn_id:
                self.warning_delivered = True
                self.events.append({'type':'warning_acknowledged','at':timestamp(),'turn_id':self.turn_id})
            else:
                self.events.append({'type':'warning_rejected','at':timestamp(),
                                    'message':message.get('error',{}).get('message','Active-turn acknowledgement did not match')})
            self.pending_steer = None
            return
        if message.get('method') == 'thread/tokenUsage/updated':
            params = message['params']
            if params['threadId'] == self.thread_id:
                total = params['tokenUsage']['total']
                # Dedicated unit thread; provider total must agree with component accounting.
                tokens = total['inputTokens'] + total['outputTokens']
                if total.get('totalTokens',tokens) != tokens:
                    self.events.append({'type':'inconsistent_usage','at':timestamp()}); return
                self.observe(tokens, 'token_usage_notification', rpc)
        elif message.get('method') == 'turn/completed':
            params = message['params']
            if params.get('threadId') == self.thread_id and params['turn']['id'] == self.turn_id:
                self.finished = True

    def outcome(self):
        if self.actual_tokens is None:
            status = 'usage_unknown'
        elif self.warning_delivered:
            status = 'warned_and_heeded' if self.actual_tokens <= self.ceiling else 'warned_and_ignored'
        elif self.crossing_total is not None:
            status = 'crossed_without_verified_delivery'
        else:
            status = 'below_threshold'
        return {'status':status,'actual_tokens':self.actual_tokens,'token_ceiling':self.ceiling,
                'baseline_tokens':self.baseline_tokens,
                'warning_delivered':self.warning_delivered,'polls_sent':sum(e['type']=='poll_sent' for e in self.events),
                'crossing_total':self.crossing_total,'events':self.events}
