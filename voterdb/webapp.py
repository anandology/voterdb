import web
import json
from loader import db

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
		print locals()
		i = web.input(state="", ac="", pb="", voterid=None, offset=0, limit=100)

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

		offset = int(i.offset)
		limit = int(i.limit)
		where += " AND voter.booth_id = booth.id"
		what = "state, ac, pb, voterid, name"
		order = "state, ac, pb, serial_number"
		result = db.select("voter, booth", 
			what=what, 
			where=where, 
			order=order,
			offset=offset, 
			limit=limit).list()

		web.header("content-type", "application/json")
		return json.dumps(result)

	def where(self, **kwargs):
		print "where", kwargs
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

if __name__ == '__main__':
	app.run()