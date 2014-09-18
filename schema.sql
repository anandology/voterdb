
create table booth (
	id serial primary key,
	state char(2),
	ac smallint,
	pb smallint
);

create table voter (
	id serial primary key,
	booth_id integer references booth,
	voterid text,
	serial_number smallint,
	name text,
	age smallint,
	rel_name text,
	address text
);
