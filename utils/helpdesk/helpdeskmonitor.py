#%%
import datetime
import json
import os
import time

from tcspy.configuration import mainConfig
from tcspy.utils.connector import SlackConnector
from tcspy.utils.helpdesk import HelpdeskPortal
#%%
class HelpdeskMonitor(mainConfig):
    """
    Relays helpdesk (osTicket client portal) activity to Slack: one Slack thread per ticket.

    - New ticket            -> new channel message (thread parent)
    - New thread entry      -> thread reply (user messages and staff responses)
    - Ticket status change  -> thread reply

    Ticket state (Slack thread ts, already relayed entries) is stored in HELPDESK_STATEPATH so that
    restarts do not re-post. If the state file does not exist, the first check only records the
    current tickets without posting (no flood of old tickets).
    """

    def __init__(self):
        super().__init__()
        self.portal = HelpdeskPortal(url = self.config['HELPDESK_URL'],
                                     credential_path = self.config['HELPDESK_CREDENTIAL'])
        self.slack = None
        if self.config['HELPDESK_SLACK_CHANNEL']:
            self.slack = SlackConnector(token_path = self.config['SLACK_TOKEN'], default_channel_id = self.config['HELPDESK_SLACK_CHANNEL'])
        else:
            print('HELPDESK_SLACK_CHANNEL is not set. Slack messages will only be printed (dry run).')
        self.state_path = self.config['HELPDESK_STATEPATH']
        self.state = self._load_state()

    def monitor(self,
                check_interval : int = None):
        check_interval = check_interval or self.config['HELPDESK_CHECKINTERVAL']
        print(f'Starting helpdesk monitoring (every {check_interval} s).')
        while True:
            try:
                self.check()
            except Exception as e:
                print(f'[{datetime.datetime.now()}] Helpdesk check failed: {e}')
            time.sleep(check_interval)

    def check(self):
        """Check the portal once and relay changes to Slack."""
        print(f'[{datetime.datetime.now()}] Checking helpdesk tickets...')
        is_seeding = self.state is None
        if is_seeding:
            self.state = dict(tickets = dict())

        open_tickets = self.portal.list_tickets(status = 'open')
        closed_tickets = self.portal.list_tickets(status = 'closed', max_pages = 1)
        known = self.state['tickets']
        targets = [ticket['ticket_id'] for ticket in open_tickets]
        # Closed tickets: only new ones or ones that were open at the last check
        targets += [ticket['ticket_id'] for ticket in closed_tickets
                    if ticket['ticket_id'] not in known or known[ticket['ticket_id']]['is_open']]

        # Open/closed is decided by the portal list, not by the status name (e.g. 'Resolved' is a closed state)
        open_ids = {ticket['ticket_id'] for ticket in open_tickets}
        for ticket_id in dict.fromkeys(targets):
            try:
                ticket = self.portal.get_ticket(ticket_id)
                self._process_ticket(ticket, is_open = ticket_id in open_ids, post = not is_seeding)
            except Exception as e:
                print(f'[{datetime.datetime.now()}] Failed to process ticket {ticket_id}: {e}')
        if is_seeding:
            self._save_state()
            print(f'Initial check: {len(known)} existing tickets are recorded without posting.')

    def _process_ticket(self, ticket : dict, is_open : bool, post : bool = True):
        record = self.state['tickets'].get(ticket['ticket_id'])
        is_new = record is None
        if is_new:
            record = dict(number = ticket['number'], subject = ticket['subject'], status = ticket['status'],
                          is_open = True, slack_ts = None, entries = [])
            self.state['tickets'][ticket['ticket_id']] = record
        new_entries = [entry for entry in ticket['entries'] if entry['entry_id'] not in record['entries']]
        status_changed = (not is_new) and (record['status'] != ticket['status'])

        if post and (is_new or new_entries or status_changed):
            if record['slack_ts'] is None:
                record['slack_ts'] = self._post(self._format_ticket(ticket))
                self._save_state()
            for entry in new_entries:
                self._post(self._format_entry(entry), thread_ts = record['slack_ts'])
                record['entries'].append(entry['entry_id'])
                self._save_state()
            if status_changed:
                self._post(f":arrows_counterclockwise: Status changed: *{self._escape(record['status'])}* → *{self._escape(ticket['status'])}*",
                           thread_ts = record['slack_ts'])
        elif not post:
            record['entries'] = [entry['entry_id'] for entry in ticket['entries']]

        record.update(number = ticket['number'], subject = ticket['subject'], status = ticket['status'],
                      is_open = is_open)
        self._save_state()

    def _post(self, text : str, thread_ts : str = None):
        if self.slack is None:
            print(f'[DRY RUN] (thread_ts = {thread_ts})\n{text}\n')
            return f'dryrun-{time.time()}'
        if thread_ts is None:
            result = self.slack.post_message(text = text)
        else:
            result = self.slack.post_thread_message(thread_ts, text = text)
        return result['ts']

    def _format_ticket(self, ticket : dict):
        return (f":ticket: *Helpdesk <{ticket['url']}|#{ticket['number']}>*: {self._escape(ticket['subject'])}\n"
                f"Status: {self._escape(ticket['status'])}  |  Department: {self._escape(ticket['department'])}  |  Created: {self._escape(ticket['created'])}")

    def _format_entry(self, entry : dict, max_length : int = 2500):
        icon, label = dict(message = (':speech_balloon:', 'message'),
                           response = (':incoming_envelope:', 'staff response')).get(entry['type'], (':memo:', entry['type']))
        body = entry['body']
        if len(body) > max_length:
            body = body[:max_length] + ' ... (truncated)'
        text = f"{icon} *{self._escape(entry['poster'])}* ({label}) · {self._escape(entry['time'])}"
        if body:
            text += '\n' + '\n'.join('> ' + line for line in self._escape(body).split('\n'))
        if entry['attachments']:
            text += '\n:paperclip: ' + ', '.join(self._escape(name) for name in entry['attachments'])
        return text

    @staticmethod
    def _escape(text : str):
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    def _load_state(self):
        if not os.path.isfile(self.state_path):
            return None
        with open(self.state_path, 'r') as f:
            return json.load(f)

    def _save_state(self):
        os.makedirs(os.path.dirname(self.state_path), exist_ok = True)
        tmp_path = self.state_path + '.tmp'
        with open(tmp_path, 'w') as f:
            json.dump(self.state, f, indent = 4)
        os.replace(tmp_path, self.state_path)
# %%
if __name__ == "__main__":
    helpdeskmonitor = HelpdeskMonitor()
#%%
if __name__ == "__main__":
    helpdeskmonitor.monitor()
# %%
