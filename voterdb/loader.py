"""Script to load voterids into the database.

The script takes multiple filenames, each containing list of voterids.
The state is infered from the directory of the file and AC/PB are
extracted from the filename.
"""
import sys
import os
import re
import web

db = web.database(dbn="postgres", db="voterdb")

# First we download the voterlist PDFs from ceo website
# and generate .txt file for each PDF. The filenames are 
# as provided on the ceo website of corresponding state.
patterns = {
    "KL": re.compile("([0-9]{3})([0-9]{3}).txt"),
    "DL": re.compile("A([0-9]{3})([0-9]{4}).txt"),
    "MP": re.compile("S12A([0-9]{3})P([0-9]{3}).txt"),
}

class Loader:
    def __init__(self):
        self.booths = {}

    def parse_path(self, path):
        """Parses the filename and returns state, ac number and pb number.
        """
        # foo/bar/MP/S12A012P123.txt -> MP
        state = os.path.basename(os.path.dirname(path))
        filename = os.path.basename(path)
        ac, pb = patterns[state].match(filename).groups()
        return state, int(ac), int(pb)

    def load_state(self, state):
        """Loads all booths in the given state.
        """
        result = db.where("booth", state=state)
        booths = [Booth(row) for row in result]
        self.booths.update(((b.state, b.ac, b.pb), b) for b in booths)

    def load_booths(self, filenames):
        data = [self.parse_path(f) for f in filenames]
        states = set(state for state, ac, pb in data)
        for s in states:
            self.load_state(s)

        inserts = []
        for state, ac, pb in data:
            if (state, ac, pb) not in self.booths:
                inserts.append(dict(state=state, ac=ac, pb=pb))

        if inserts:
            db.multiple_insert("booth", inserts)

            # load states again after inserts
            for s in states:
                self.load_state(s)
            
    def load(self, filenames):
        self.load_booths(filenames)
        for f in filenames:
            state, ac, pb = self.parse_path(f)
            booth = self.booths[state, ac, pb]
            booth.load(f)

class Booth(web.storage):
    def load(self, filename):
        voterids = (line.strip() for line in open(filename))
        data = [dict(booth_id=self.id, voterid=v) for v in voterids]
        db.multiple_insert("voter", data)

def main():
    filenames = sys.argv[1:]
    loader = Loader()
    loader.load(filenames)

if __name__ == "__main__":
    main()
