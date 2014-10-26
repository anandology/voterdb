import sys
import web
import json
from loader import db
import logging
from . import voterlib

urls = (
    "/", "index",
    "/voters", "voters",
    "/voters/([A-Z][A-Z])", "voters",
    "/voters/([A-Z][A-Z])/(\d+)", "voters",
    "/voters/([A-Z][A-Z])/(\d+)/(\d+)", "voters",
)
app = web.application(urls, globals())
application = app.wsgifunc()

class index:
    def GET(self):
        return "Hello, world!"

class voters:
    def GET(self, state=None, ac=None, pb=None):
        i = web.input(offset=0, limit=100)
        where = self.construct_where(state=state, ac=ac, pb=pb)

        # ensure voter info is loaded
        #self.POST(state=state, ac=ac, pb=pb)

        offset = int(i.offset)
        limit = int(i.limit)
        where += " AND voter.booth_id = booth.id"
        what = "state, ac, pb, voterid, name, address"
        order = "state, ac, pb"
        result = db.select("voter, booth",
            what=what,
            where=where,
            order=order,
            offset=offset,
            limit=limit).list()

        web.header("content-type", "application/json")
        return json.dumps(result)

    def POST(self, state=None, ac=None, pb=None):
        where = self.construct_where(state=state, ac=ac, pb=pb) + " AND name is NULL"
        result = db.select("voter, booth",
            what="voterid",
            where=where,
            limit=100).list()
        data = [voterlib.get_voter_info(row.voterid) for row in result]
        with db.transaction():
            for row in data:
                print row
                db.update("voter", where="voterid=$epic_no", vars=row,
                    serial_number=row['slno_inpart'],
                    name=row['name'],
                    name2=row['name_v1'],
                    rel_name=row['rln_name'],
                    rel_name2=row['rln_name_v1'],
                    gender=row['gender'],
                    age=row['age'],
                    address=row['house_no'])

    def construct_where(self, state=None, ac=None, pb=None):
        i = web.input(state="", ac="", pb="", voterid=None)

        def split(value):
            return value and value.split(",") or None

        if pb:
            where = self.where(state=state, ac=ac, pb=pb)
        elif ac:
            where = self.where(state=state, ac=ac, pb=split(i.pb))
        elif state:
            where = self.where(state=state, ac=split(i.ac))
        else:
            where = self.where(state=split(i.state), voterid=split(i.voterid))
        return where

    def where(self, **kwargs):
        conditions = []
        for k, v in kwargs.items():
            if not v: # ignore None and empty lists
                continue
            elif isinstance(v, list):
                conditions.append(web.reparam(k + " in $v", locals()))
            else:
                conditions.append(web.reparam(k + "=$v", locals()))
        if not conditions:
            return "1=1"
        return web.SQLQuery.join(conditions, " AND ")

def load_voterinfo(booth_id):
    logging.info("loading voterinfo for booth id %s", booth_id)

    booth = db.select("booth", where="id=$booth_id", vars=locals())
    search = voterlib.get_voter_search(booth.state)

    result = db.select("voter",
        what="voterid",
        where="name is NULL and booth_id=$booth_id",
        limit=10,
        vars=locals()).list()

    data = [search.get_voter_info(row.voterid) for row in result]
    with db.transaction():
        for row in data:
            if not row:
                return
            print row
            db.update("voter", where="voterid=$epic_no", vars=row,
                serial_number=row['slno_inpart'],
                name=row['name'],
                name2=row['name_v1'],
                rel_name=row['rln_name'],
                rel_name2=row['rln_name_v1'],
                gender=row['gender'],
                age=row['age'],
                address=row['house_no'])


def main():
    FORMAT = "%(asctime)-15s %(levelname)s %(message)s"
    logging.basicConfig(level=logging.INFO, format=FORMAT)

    if "--load" in sys.argv:
        sys.argv.remove("--load")
        booth_id = int(sys.argv[1])
        load_voterinfo(booth_id)
    else:
        app.run()

if __name__ == '__main__':
    main()
