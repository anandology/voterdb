import requests
import re
import logging
import sys
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
    RE_LINK = re.compile('.*href="([^"]*)">.*')

    def __init__(self):
        self.session = requests.session()
        self.cache = {}

    def get_voter_info(self, voterid):
        logger.info("fetching voterinfo for %s", voterid)
        if voterid in self.cache:
            return self.cache[voterid]

        url = self.URL_PATTERN.format(voterid)
        r = self.session.get(url).json()
        if r.get('aaData'):
            row = r['aaData'][0]
            return self.read_details(voterid, row)

    def read_details(self, voterid, row):
        name, rln_name, address, slno_inpart, ac_no, part_no, link_text, status = row
        if status.lower() != 'active':
            return
        link = "http://www.ceo.kerala.gov.in/" + self.RE_LINK.match(link_text).group(1)            

        details = dict(epic_no=voterid,
                    slno_inpart=slno_inpart,
                    name=name,
                    rln_name=rln_name,
                    address=address)
        html = self.session.get(link).text
        # uncomment. The names in Malayalam are in comments.
        html = html.replace("<!--", "XXXX").replace("-->", "")
        soup = BeautifulSoup(html, 'lxml')
        trs = soup.find("table").find_all("tr")
        data = [[td.get_text().strip() for td in tr.find_all("td")] for tr in trs]

        name, name_v1 = data[1][1].split("XXXX")
        age = data[2][1]
        rln_name, rln_name_v1 = data[3][1].split("XXXX")
        address, address_v1 = data[4][1].split("XXXX")

        details['name_v1'] = name_v1.strip()
        details['age'] = age.strip()
        details['rln_name_v2'] = rln_name_v1.strip()
        details['house_no'] = address.strip()

        house_no = address.strip().split("/")[0]
        self.cache_other_family_members(house_no, soup)

        return details

    def cache_other_family_members(self, house_no, soup):
        # find other members in the famility to avoid requests for them.
        table = soup.find_all("table")[2]
        for tr in table.find_all("tr")[1:]:
            name, rln_name, house_name, slno_inpart, ac, ps, voterid, status = [td.get_text().strip() for td in tr.find_all("td")]
            logger.info("caching details for %s", voterid)
            if status.lower() != "active":
                self.cache[voterid] = None
            else:
                address = u"{} / {}".format(house_no, house_name)
                self.cache[voterid] = dict(
                    epic_no=voterid,
                    slno_inpart=slno_inpart,
                    name=name,
                    rln_name=rln_name,
                    house_no=address)


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

def main():
    FORMAT = "%(asctime)-15s %(levelname)s %(message)s"
    logging.basicConfig(level=logging.INFO, format=FORMAT)
    v = KeralaVoterSearch()
    for voterid in sys.argv[1:]:
        print v.get_voter_info(voterid)

if __name__ == "__main__":
    main()