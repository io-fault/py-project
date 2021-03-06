"""
# Analyze polynomial using temporary directories.
"""
import itertools

from ...system import files

from .. import types
from .. import polynomial as module

python_factor_typref = types.Reference(
	'http://if.fault.io/factors',
	types.factor@'python.module',
	'type',
	'python.psf-v3',
)

text_factor_typref = types.Reference(
	'http://if.fault.io/factors',
	types.factor@'text.chapter',
	'type',
	'kleptic',
)

exe_typref = types.Reference(
	'http://if.fault.io/factors',
	types.factor@'system.executable',
	'type',
	None,
)

extmap = {
	'py': (python_factor_typref, set()),
	'txt': (text_factor_typref, set()),
}

def mkfactor(ftype, symbols):
	header = "! CONTEXT:\n\t/protocol/\n\t\t&<http://if.fault.io/project/factor>\n"
	fmt = "/{key}/\n\t`{value}`\n"
	sym = "- `{sym}`"
	if symbols:
		lines = [sym.format(sym=x) for x in symbols]
		syms = "/symbols/\n\t" + '\n\t'.join(lines)
	else:
		syms = ""

	return header + \
		fmt.format(key='type', value=ftype) + \
		syms

def test_V1_isource(test):
	td = test.exits.enter_context(files.Path.fs_tmpdir())
	p = module.V1({})

	vf = (td/'valid.c').fs_init()
	test/p.isource(vf) == True

	invalid = (td/'filename').fs_init()
	test/p.isource(invalid) == False

	dotfile = (td/'.filename').fs_init()
	test/p.isource(dotfile) == False

def test_V1_collect_explicit_sources(test):
	td = test.exits.enter_context(files.Path.fs_tmpdir())
	p = module.V1({})
	typcache = p.source_format_resolution()
	unknown = module.unknown_factor_type

	vf = (td/'valid.c').fs_init()
	sub = (td@"path/to/inner.c").fs_init()

	ls = list(p.collect_explicit_sources(typcache, td))
	test/((unknown, vf) in ls) == True
	test/((unknown, sub) in ls) == True

def test_V1_iterfactors_explicit_known(test):
	td = test.exits.enter_context(files.Path.fs_tmpdir())
	p = module.V1({'source-extension-map': extmap})

	vf = (td/'valid.c').fs_init()
	pt = (td/'project.txt').fs_init()
	py = (td/'test.py').fs_init()

	idx = dict(p.iterfactors(td, types.factor))
	test/len(idx) == 3
	sources = list(itertools.chain(*[x[-1] for x in idx.values()]))

	(module.unknown_factor_type, vf) in test/sources
	(text_factor_typref, pt) in test/sources

	py_seg = types.FactorPath.from_sequence(['test'])
	py_struct = idx[(py_seg, python_factor_typref.isolate(None))]
	test/py_struct == (set(), [(python_factor_typref, py)])

def test_V1_iterfactors_explicit_unknown(test):
	td = test.exits.enter_context(files.Path.fs_tmpdir())
	p = module.V1({'source-extension-map': extmap})

	ft = (td/'cf'/'factor.txt').fs_init(mkfactor(str(exe_typref), set()).encode('utf-8'))

	v = (td/'cf'/'src'/'valid.c').fs_init()
	fs = dict(p.iterfactors(td, types.factor))

	cf = types.FactorPath.from_sequence(['cf'])
	fls = list(fs[(cf, exe_typref)][-1])
	test/len(fls) == 1
	(module.unknown_factor_type, v) in test/fls

def test_V1_information(test):
	"""
	# - &module.V1.information
	"""
	td = test.exits.enter_context(files.Path.fs_tmpdir())

	src = types.Information(**{
		'identifier': 'http://fault.io/test',
		'name': 'test',
		'icon': {
			'category': 'test-category',
		},
		# Current consistent with text.types.Paragraph
		'abstract': [('text/normal', "Project information for testing purposes.")],
		'authority': "Fault Engineering",
		'contact': "http://fault.io/critical",
	})

	fake = b"! CONTEXT:\n\t/protocol/\n\t\t&<http://if.fault.io/project/information>\n"
	fake += b"/identifier/\n\t`http://fault.io/test\n"
	fake += b"/name/\n\t`test`\n"
	fake += b"/icon/\n\t- (category)`test-category`\n"
	fake += b"/abstract/\n\tProject information for testing purposes.\n"
	fake += b"/authority/\n\tFault Engineering\n"
	fake += b"/contact/\n\thttp://fault.io/critical\n"

	pi = (td/'test'/'project.txt').fs_init(fake)
	p = module.V1({})
	data = p.information(td/'test')
	test/data == src

if __name__ == '__main__':
	import sys
	from fault.test import library as libtest
	libtest.execute(sys.modules[__name__])
