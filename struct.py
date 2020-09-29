"""
# Interpret a fault.text encoded project data structure.

# &protocol contains the supported types.
"""
import typing

from ..text import document
from ..text import format
from ..text.types import Paragraph

def _project_interpret(obj):
	t = obj[0]
	if t == 'paragraph':
		first = document.paragraph_only(obj)
		if first is None:
			return document.paragraph_as_string(obj)
		else:
			return document.interpret_paragraph_single(first)
	elif t == 'set':
		c = obj[1]
		c = [document.paragraph_first(x[1][0]) for x in c]
		r = dict([(x[-1].get('cast'), (x[1][0])) for x in c])
		return r

def _factor_field_i(obj):
	t = obj[0]
	if t == 'paragraph':
		# Linked identifier.
		first = document.paragraph_only(obj)
		if first is None:
			return document.paragraph_as_string(obj)
		else:
			return document.interpret_paragraph_single(first)

def _requirement_i(obj):
	for t in obj:
		if t[0] in {'set', 'sequence'}:
			for i in t[1]:
				yield document.paragraph_as_string(i[1][0])
		else:
			yield document.paragraph_as_string(t)

def _symbol_i(obj):
	if obj[0] in {'set', 'sequence'}:
		for t in obj[1]:
			yield document.export(t[1][0][1])
	else:
		yield document.export(obj[1])

def _context_data(section):
	# Currently limited to sections only containing one admonition.
	a = section
	k = dict([(k, (v, p)) for k, v, p in a])
	context_admonition = k.pop('admonition', None)
	ctx = None

	if context_admonition:
		if context_admonition[1]['type'] == 'CONTEXT':
			ctx = document.context(context_admonition)
			for x in ctx:
				v = ctx[x]
				if v[0] == 'paragraph':
					ctx[x] = document.export(v[1])
				elif v[0] == 'syntax':
					ctx[x] = document.concatenate(v)

	return ctx, k

def project(data):
	main_dict = {
		e[1][0][1][0]: (e[1][1][1][0]) for e in data[0]
	}
	abs_para = main_dict.pop('abstract')[1] # FORMAT: /abstract/ field not found.
	id_para_nodes = main_dict.pop('identifier')[1] # FORMAT: /identifier/ field not found.

	id_para = document.export([x for x in id_para_nodes if x])
	id_frag = id_para.sole

	# Trim
	for i in range(len(abs_para)):
		if abs_para[i]:
			break
	del abs_para[:i]
	for i in range(len(abs_para)-1, 0, -1):
		if abs_para[i]:
			break
	del abs_para[i+1:]

	main_dict = {k:_project_interpret(v) for k,v in main_dict.items()}
	main_dict['abstract'] = document.export(abs_para)
	main_dict['identifier'] = id_frag[1]

	# Redirect to authority.
	if 'controller' in main_dict:
		main_dict['authority'] = main_dict.pop('controller')

	return main_dict

def infras(data):
	main = (
		(e[1][0][1][0], (e[1][1][1][0])) for e in data[0]
	)

	rd = {}
	for k, v in main:
		if v[0] in {'set', 'sequence'}:
			rd[k] = set(document.export(x[1][0][1]).sole for x in v[1]) # One fragment in item
		else:
			rd[k] = document.export(v[1])

	return rd

def factor(data):
	main_dict = {
		e[1][0][1][0]: (e[1][1][1]) for e in data[0]
	}

	ftype = main_dict['type'] # FORMAT: /type/ must be declared within the first dictionary.
	main_dict['type'] = _factor_field_i(ftype[0])

	domain = main_dict.get('domain') # Optional; usually defaults to 'system'.
	if domain is not None:
		main_dict['domain'] = _factor_field_i(domain[0])
	else:
		main_dict['domain'] = None

	reqs = main_dict.get('symbols') # Optional; defaults to empty set.
	if reqs is not None:
		main_dict['symbols'] = set(_requirement_i(reqs))

	return main_dict

protocol = {
	"http://if.fault.io/project/information": project,
	"http://if.fault.io/project/infrastructure": infras,
	"http://if.fault.io/project/snapshot": None,
	"http://if.fault.io/project/factor": factor
}

def _parse(source,
		Parser=format.Parser,
		Transform=document.Transform,
		dt=document.Tree()
	):
	dx = Transform(dt)
	fp = Parser()
	return dx.process(fp.parse(source))

def parse(text:str) -> typing.Tuple[object, object]:
	try:
		tree = _parse(text)
		context, main = _context_data(tree[1])
		proto = context['protocol'][0][-1] # FORMAT: /protocol/ not found in CONTEXT admonition.
		si = protocol[proto] # FORMAT: protocol not supported by fault.text.struct
		struct = si(main.pop('dictionary'))
	except Exception as err:
		raise ValueError("unrecognized text structure") from err

	return context, struct

if __name__ == '__main__':
	import sys
	import pprint
	pprint.pprint(parse(sys.stdin.read()))
