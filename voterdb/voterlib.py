import requests
import re
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "http://electoralsearch.in/"

class VoterSearch:
    def __init__(self):
        self._token = None
        self.session = requests.session()

    def get_token(self):
        if self._token is None:
            r = self.session.get(BASE_URL)
            # extract the token hidden in javascript
            self._token = get_token(r.text)
        return self._token

    def get_voter_info(self, voterid):
        logger.info("fetching voterinfo for %s", voterid)
        token = self.get_token()
        print "token", token

        # prepare search parameters
        params = {
            'epic_no': voterid,
            'page_no': '1',
            'results_per_page': 5,
            'reureureired': token,
            'search_type': 'epic'
        }

        # The electoralsearch website refuses to give results if it Referer
        # header is not set. 
        headers = {"Referer": BASE_URL, "User-agent": "Mozilla"}

        # Make the search request
        r = self.session.get(BASE_URL + "Search", params=params, headers=headers)

        # and read json from it
        try:
            d = r.json()
            print d
            return d['response']['docs'][0]
        except (KeyError, IndexError, ValueError, TypeError):
            logger.error("failed - %s %s", voterid, d)
            pass

class KeralaVoterSearch:
    URL_PATTERN = "http://www.ceo.kerala.gov.in/electoralroll/edetailListAjax.html?epicNo={}"
    def __init__(self):
        self.session = requests.session()

    def get_voter_info(self, voterid):
        logger.info("fetching voterinfo for %s", voterid)
        url = self.URL_PATTERN.format(voterid)
        r = self.session.get(url).json()
        if r.get('aaData'):
            row = r['aaData'][0]
            return self.read_details(row)

    def read_details(self, voterid, row):
        name, rln_name, address, slno_inpart, ac_no, part_no, link, status = r['aaData'][0]
        if status.lower() != 'active':
            return

        details = dict(epic_no=voterid,
                    slno_inpart=slno_inpart,
                    name=name,
                    rln_name=rln_name,
                    address=address)
        html = self.session.get(url).text
        # uncomment. The names in Malayalam are in comments.
        html.replace("<!--", "XXXX").replace("-->", "")
        soup = BeautifulSoup(html, 'lxml')
        trs = soup.find("table").find_all("tr")
        data = dict([td.get_text().strip() for td in tr.find_all("td")] for tr in trs)

        name, name_v1 = data[1].split("XXXX")
        age = data[2]
        rln_name, rln_name_v1 = data[3].split("XXXX")
        address, address_v1 = data[4].split("XXXX")

        details['name_v1'] = name_v1.strip()
        details['age'] = age.strip()
        details['rln_name_v2'] = rln_name_v1.strip()
        details['address'] = address.strip()
        return details

def get_voter_search(state):
    if state == 'KL':
        return KeralaVoterSearch()
    else:
        return VoterSearch()

def get_voter_info(voterid):
    v = KeralaVoterSearch()
    print v.get_voter_info(voterid)

re_token = re.compile("function _aquire\(\) *{ *return '([0-9a-f-]+)';")
def get_token(text):
    """The extracts the token burried in some javascript.

    The electoralsearch website keeps a UUID in a javascript function and
    that is required for searching for voterid. This function extracts that
    using regular expressions.
    """
    text = " ".join(text.splitlines())
    m = re_token.search(text)
    return m and m.group(1)

if __name__ == "__main__":
	import sys
	print get_voter_info(sys.argv[1])
