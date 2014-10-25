import requests
import re
import logging

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

def get_voter_info(voterid):
    v = VoterSearch()
    print v.get_voter_info(voterid)
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
