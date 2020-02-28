"""
# Analyze polynomial using temporary directories.
"""
import itertools

from ... import routes
from ...system import files

from .. import core
from .. import polynomial as module

extmap = {
	'py': ('python', 'module', set()),
	'txt': ('void', 'data', set()),
}

def mkfactor(ftype, fdomain, symbols):
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
		fmt.format(key='domain', value=fdomain) + \
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

def test_V1_collect_sources(test):
	td = test.exits.enter_context(files.Path.fs_tmpdir())
	p = module.V1({})

	vf = (td/'valid.c').fs_init()
	sub = (td@"path/to/inner.c").fs_init()

	ls = list(p.collect_sources(td))
	test/(vf in ls) == True
	test/(sub in ls) == True

def test_V1_iterfactors_whole(test):
	td = test.exits.enter_context(files.Path.fs_tmpdir())
	p = module.V1({'source-extension-map': extmap})

	vf = (td/'valid.c').fs_init()
	pt = (td/'project.txt').fs_init()
	py = (td/'test.py').fs_init()

	idx = dict(p.iterfactors(td))
	test/len(idx) == 3
	sources = list(itertools.chain(*[x[-1] for x in idx.values()]))

	vf in test/sources
	pt in test/sources

	py_seg = core.FactorPath.from_sequence(['test'])
	py_struct = idx[py_seg]
	test/py_struct == ('python', 'module', set(), [py])

def test_V1_iterfactors_composite(test):
	td = test.exits.enter_context(files.Path.fs_tmpdir())
	p = module.V1({'source-extension-map': extmap})

	ft = (td/'cf'/'factor.txt').fs_init(mkfactor('executable', 'system', set()).encode('utf-8'))

	v = (td/'cf'/'src'/'valid.c').fs_init()
	fs = dict(p.iterfactors(td))

	cf = core.FactorPath.from_sequence(['cf'])
	fls = list(fs[cf][-1])
	test/len(fls) == 1
	v in test/fls
	test/fs[cf][:2] == ('system', 'executable')

def test_V1_iterfactors_implied_composite(test):
	td = test.exits.enter_context(files.Path.fs_tmpdir())
	p = module.V1({'source-extension-map': extmap})

	for it in p.implicit_types:
		d = (td/it).fs_mkdir()

		v = (d/('cf.'+it)/'valid.c').fs_init()
		fs = dict(p.iterfactors(d))

		cf = core.FactorPath.from_sequence(['cf'])
		fls = list(fs[cf][-1])
		test/len(fls) == 1
		v in test/fls
		test/fs[cf][:2] == ('system', p.implicit_types[it])

def test_V1_information(test):
	"""
	# - &module.V1.information
	"""
	td = test.exits.enter_context(files.Path.fs_tmpdir())

	src = core.Information(**{
		'identifier': 'http://fault.io/test',
		'name': 'test',
		'icon': {
			'category': 'test-category',
		},
		# Current consistent with text.types.Paragraph
		'abstract': [('text/normal', "Project information for testing purposes.")],
		'controller': "Fault Engineering Laboratories",
		'contact': "http://fault.io/critical",
	})

	fake = b"! CONTEXT:\n\t/protocol/\n\t\t&<http://if.fault.io/project/information>\n"
	fake += b"/identifier/\n\t`http://fault.io/test\n"
	fake += b"/name/\n\t`test`\n"
	fake += b"/icon/\n\t- (category)`test-category`\n"
	fake += b"/abstract/\n\tProject information for testing purposes.\n"
	fake += b"/controller/\n\tFault Engineering Laboratories\n"
	fake += b"/contact/\n\thttp://fault.io/critical\n"

	pi = (td/'test'/'project.txt').fs_init(fake)
	p = module.V1({})
	fc = core.FactorContextPaths(td, core.factor, td/'test')
	data = p.information(fc)
	test/data == src

if __name__ == '__main__':
	import sys
	from fault.test import library as libtest
	libtest.execute(sys.modules[__name__])
