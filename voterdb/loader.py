"""Script to load voterids into the database.

The script takes multiple filenames, each containing list of voterids.
The state is infered from the directory of the file and AC/PB are
extracted from the filename.

This doesn't actually load the voterids into the database, but provides in a 
form that is faster to load into database. This script creates enties for all 
booths if required and prints booth_id and voterid columns. The user is expected
to use the output and load it into the database. Here is the typical workflow:

    python voterdb/loader.py MP/*.txt > MP-data.txt
    mkdir parts
    split -l 1000000 MP-data.txt parts/MP-
    for f in parts/MP-*;
    do 
        echo $f
        psql voterdb -c "COPY voter (booth_id, voterid) FROM STDIN" < $f
    done
"""
import sys
import os
import re
import web
from logbook import Logger

logger = Logger('voterdb.loader')

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
            data = booth.load(f)
            for booth_id, voterid in data:
                yield booth_id, voterid

class Booth(web.storage):
    def load(self, filename):
        logger.info("loading {}".format(filename))
        voterids = (line.strip() for line in open(filename))
        return ((self.id, v) for v in voterids)

def main():
    filenames = sys.argv[1:]
    loader = Loader()
    data = loader.load(filenames)
    for booth_id, voterid in data:
        print str(booth_id) + "\t" + voterid

if __name__ == "__main__":
    main()
