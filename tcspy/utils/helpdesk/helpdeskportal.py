#%%
import json
import re
from html.parser import HTMLParser
from urllib.parse import urljoin

import requests
#%%
class _Element:
    def __init__(self, tag, attrs, parent = None):
        self.tag = tag
        self.attrs = dict(attrs)
        self.parent = parent
        self.children = []  # _Element or str

    @property
    def classes(self):
        return (self.attrs.get('class') or '').split()

    def iter(self):
        for child in self.children:
            if isinstance(child, _Element):
                yield child
                yield from child.iter()

    def find_all(self, tag = None, id_ = None, class_ = None, id_prefix = None):
        for el in self.iter():
            if tag and el.tag != tag:
                continue
            if id_ and el.attrs.get('id') != id_:
                continue
            if id_prefix and not (el.attrs.get('id') or '').startswith(id_prefix):
                continue
            if class_ and class_ not in el.classes:
                continue
            yield el

    def find(self, **kwargs):
        return next(self.find_all(**kwargs), None)

    def text(self, block_newlines = False):
        """Concatenated text. With block_newlines, block-level tags are separated by newlines."""
        parts = []
        blocks = ('p', 'div', 'li', 'tr', 'h1', 'h2', 'h3', 'h4', 'blockquote', 'pre', 'table')
        def walk(el):
            for child in el.children:
                if isinstance(child, str):
                    parts.append(child)
                elif child.tag == 'br':
                    parts.append('\n')
                else:
                    if block_newlines and child.tag in blocks:
                        parts.append('\n')
                    walk(child)
                    if block_newlines and child.tag in blocks:
                        parts.append('\n')
        walk(self)
        text = ''.join(parts)
        if block_newlines:
            lines = [re.sub(r'[ \t\xa0]+', ' ', line).strip() for line in text.split('\n')]
            text = re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()
        else:
            text = re.sub(r'\s+', ' ', text.replace('\xa0', ' ')).strip()
        return text

class _TreeBuilder(HTMLParser):
    """Minimal, tolerant HTML -> _Element tree (stdlib only)."""
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}

    def __init__(self):
        super().__init__(convert_charrefs = True)
        self.root = _Element('root', [])
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        el = _Element(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(el)
        if tag not in self.VOID:
            self.stack.append(el)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(_Element(tag, attrs, self.stack[-1]))

    def handle_endtag(self, tag):
        # Close up to the matching open tag; ignore stray end tags
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if self.stack[-1].tag not in ('script', 'style'):
            self.stack[-1].children.append(data)

def parse_html(html : str) -> _Element:
    builder = _TreeBuilder()
    builder.feed(html)
    builder.close()
    return builder.root
#%%
class HelpdeskPortal:
    """
    Read-only client for the osTicket (v1.18) client portal.
    Only tickets visible to the logged-in account (owner or collaborator) are accessible.

    Parameters
    ----------
    url : str
        Base URL of the helpdesk (e.g. 'https://helpdesk.obstech.cl/').
    credential_path : str
        JSON file containing {"username": "...", "password": "..."}.
    """

    def __init__(self,
                 url : str,
                 credential_path : str,
                 timeout : float = 30):
        self.url = url.rstrip('/') + '/'
        self.credential_path = credential_path
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers['User-Agent'] = 'TCSpy-HelpdeskMonitor'

    def __repr__(self):
        return f"<HelpdeskPortal(url='{self.url}')>"

    def ticket_url(self, ticket_id):
        return urljoin(self.url, f'tickets.php?id={ticket_id}')

    def login(self):
        with open(self.credential_path, 'r') as f:
            credential = json.load(f)
        response = self.session.get(urljoin(self.url, 'login.php'), timeout = self.timeout)
        response.raise_for_status()
        form = parse_html(response.text).find(tag = 'form', id_ = 'clientLogin')
        if form is None:
            raise RuntimeError('Login form is not found on the helpdesk login page.')
        token = next((el.attrs.get('value') for el in form.find_all(tag = 'input') if el.attrs.get('name') == '__CSRFToken__'), None)
        data = dict(__CSRFToken__ = token,
                    luser = credential['username'],
                    lpasswd = credential['password'])
        response = self.session.post(urljoin(self.url, 'login.php'), data = data, timeout = self.timeout)
        response.raise_for_status()
        if self._is_login_page(response.text):
            raise RuntimeError('Helpdesk login failed. Check the username/password in the credential file.')
        print('Helpdesk login successful.')

    def _is_login_page(self, html : str):
        return 'id="clientLogin"' in html

    def _get(self, path : str, params : dict = None):
        """GET a portal page, logging in again when the session has expired."""
        for attempt in range(2):
            response = self.session.get(urljoin(self.url, path), params = params, timeout = self.timeout)
            response.raise_for_status()
            if not self._is_login_page(response.text):
                return response.text
            if attempt == 0:
                self.login()
        raise RuntimeError(f'Cannot access {path}: still redirected to the login page after login.')

    def list_tickets(self,
                     status : str = 'open',
                     max_pages : int = 20):
        """
        List visible tickets in the given state ('open' or 'closed'), most recent first.

        Returns
        -------
        list of dict
            Keys: ticket_id, number, created, status, subject, department
        """
        tickets = dict()
        for page in range(1, max_pages + 1):
            html = self._get('tickets.php', params = dict(a = 'search', status = status, sort = 'date', order = 'DESC', p = page))
            table = parse_html(html).find(tag = 'table', id_ = 'ticketTable')
            if table is None:
                raise RuntimeError('Ticket table is not found on tickets.php. The portal layout may have changed.')
            n_new = 0
            for row in table.find_all(tag = 'tr'):
                ticket_id = row.attrs.get('id')
                cells = [child for child in row.children if isinstance(child, _Element) and child.tag == 'td']
                if not ticket_id or len(cells) < 5 or ticket_id in tickets:
                    continue
                tickets[ticket_id] = dict(ticket_id = ticket_id,
                                          number = cells[0].text(),
                                          created = cells[1].text(),
                                          status = cells[2].text(),
                                          subject = cells[3].text(),
                                          department = cells[4].text())
                n_new += 1
            # osTicket keeps returning the last page for out-of-range page numbers
            if n_new == 0 or f'p={page + 1}' not in html:
                break
        return list(tickets.values())

    def get_ticket(self, ticket_id):
        """
        Read a ticket and its thread (user messages and staff responses; internal notes are not visible to clients).

        Returns
        -------
        dict
            Keys: ticket_id, number, subject, status, department, created, url,
                  entries (list of dict with keys: entry_id, type, poster, time, title, body, attachments)
        """
        root = parse_html(self._get('tickets.php', params = dict(id = ticket_id)))
        info = root.find(tag = 'table', id_ = 'ticketInfo')
        if info is None:
            raise RuntimeError(f'Ticket {ticket_id} is not accessible or the portal layout has changed.')
        title = info.find(tag = 'h1')
        number = title.find(tag = 'small')
        subject = title.find(tag = 'b')
        fields = dict()
        for th in info.find_all(tag = 'th'):
            td = th.parent.find(tag = 'td') if th.parent is not None else None
            if td is not None:
                fields[th.text().rstrip(':').strip()] = td.text()

        entries = []
        thread = root.find(id_ = 'ticketThread')
        for wrapper in (thread.find_all(tag = 'div', id_prefix = 'thread-entry-') if thread is not None else []):
            entry = wrapper.find(tag = 'div', class_ = 'thread-entry')
            if entry is None:
                continue
            header = entry.find(tag = 'div', class_ = 'header')
            body = entry.find(tag = 'div', class_ = 'thread-body')
            poster = header.find(tag = 'b') if header is not None else None
            time_ = header.find(tag = 'time') if header is not None else None
            entry_title = header.find(tag = 'span', class_ = 'title') if header is not None else None
            attachments = [a.text() for a in body.find_all(tag = 'a', class_ = 'filename')] if body is not None else []
            body_text = ''
            if body is not None and body.children:
                content = next((child for child in body.children if isinstance(child, _Element) and child.tag == 'div'), None)
                body_text = content.text(block_newlines = True) if content is not None else ''
            entry_type = next((cls for cls in entry.classes if cls in ('message', 'response', 'note')), 'unknown')
            entries.append(dict(entry_id = wrapper.attrs['id'][len('thread-entry-'):],
                                type = entry_type,
                                poster = poster.text() if poster is not None else '',
                                time = (time_.attrs.get('title') or time_.text()) if time_ is not None else '',
                                title = entry_title.text() if entry_title is not None else '',
                                body = body_text,
                                attachments = attachments))

        return dict(ticket_id = str(ticket_id),
                    number = number.text().lstrip('#') if number is not None else '',
                    subject = subject.text() if subject is not None else '',
                    status = fields.get('Ticket Status', ''),
                    department = fields.get('Department', ''),
                    created = fields.get('Create Date', ''),
                    url = self.ticket_url(ticket_id),
                    entries = entries)
# %%
