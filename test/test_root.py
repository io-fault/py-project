"""
# Product directory interface checks.
"""
from ...system import files
from .. import root as module
from ..types import factor, Protocol

t_project_id = 'http://ni.fault.io/test/project'

def setup(pd, local_id='', project='project'):
	pj = (pd/project).fs_mkdir()
	pid = (t_project_id + local_id).encode('utf-8')
	(pj/'.protocol').fs_init(pid + b' factors/polynomial-1')

def test_Product_attributes(test):
	pd = module.Product(files.root)
	Class = files.root.__class__
	test.isinstance(pd.project_index_route, Class)
	test.isinstance(pd.context_index_route, Class)

def test_Product_import(test):
	"""
	# - &module.Product.import_protocol
	"""
	for name in module.protocols:
		pn = module.Product.import_protocol(name)
		test.issubclass(pn, Protocol)

def test_iterprojects_root_no_context(test):
	"""
	# - &module.Product.iterprojects
	"""
	td = test.exits.enter_context(files.Path.fs_tmpdir())
	pdr = (td/'product').fs_mkdir()
	setup(pdr)

	pd = module.Product(pdr)
	pj, = pd.iterprojects()
	pid, proto, pjdir = pj

	test/pid == t_project_id
	test/proto == 'factors/polynomial-1'
	test/pjdir == pdr/'project'

def test_itercontexts_root_none(test):
	"""
	# - &module.Product.itercontexts
	"""
	# No contexts.
	td = test.exits.enter_context(files.Path.fs_tmpdir())
	pdr = (td/'product').fs_mkdir()
	setup(pdr)

	pd = module.Product(pdr)
	test/list(pd.itercontexts()) == []

def test_itercontexts_root_one(test):
	"""
	# - &module.Product.itercontexts
	"""
	# One contexts.
	td = test.exits.enter_context(files.Path.fs_tmpdir())
	pdr = (td/'product').fs_mkdir()
	ctx = (pdr/'ctx').fs_mkdir()
	setup(ctx, project='context')

	pd = module.Product(pdr)
	test/list(pd.itercontexts()) == [ctx]

def test_update(test):
	"""
	# - &module.Product.update
	"""
	td = test.exits.enter_context(files.Path.fs_tmpdir())
	pdr = (td/'product').fs_mkdir()
	ctx = (pdr/'ctx').fs_mkdir()
	setup(ctx, project='context')

	pd = module.Product(pdr)
	pd.roots = {module.types.factor@'ctx'}
	pd.update()
	cctx = pd.contexts
	cprj = pd.projects

	pd.update()
	test/cctx == pd.contexts
	test/cprj == pd.projects

	test/pd.contexts << factor@'ctx'

def product_a(test):
	td = test.exits.enter_context(files.Path.fs_tmpdir())
	pdr = (td/'product').fs_mkdir()
	ctx = (pdr/'ctx').fs_mkdir()
	setup(ctx, '/first-context', project='context')
	sub = (ctx/'sub').fs_mkdir()
	setup(sub, '/second-context', project='context')
	setup(sub, '/alt-1', project='alt-1')
	setup(sub, '/alt-2', project='alt-2')

	return td, module.Product(pdr)

def test_update_nested(test):
	"""
	# - &module.Product.update
	"""
	td, pd = product_a(test)
	pd.roots = {module.types.factor@'ctx'}
	pd.update()
	cctx = pd.contexts
	cprj = pd.projects

	pd.update()
	test/cctx == pd.contexts
	test/cprj == pd.projects

	test/pd.contexts << factor@'ctx'
	test/pd.contexts << factor@'ctx.sub'

	projects = [
		'/first-context',
		'/second-context',
		'/alt-1',
		'/alt-2',
	]

	for x in projects:
		test/pd.projects << (t_project_id + x)

def test_cache_io(test):
	"""
	# - &module.Product.store
	# - &module.Product.load
	"""
	td, pd = product_a(test)
	pd.update().store()

	original = (pd.contexts, pd.projects, pd.local)
	del pd.contexts, pd.projects
	pd.load()

	test/pd.contexts << factor@'ctx'
	test/pd.contexts << factor@'ctx.sub'

	projects = [
		'/first-context',
		'/second-context',
		'/alt-1',
		'/alt-2',
	]

	for x in projects:
		test/pd.projects << (t_project_id + x)

	test/(pd.contexts, pd.projects, pd.local) == original

def test_Product_select(test):
	"""
	# - &module.Product.identifier_by_factor
	# - &module.Product.factor_by_identifier
	"""
	td, pd = product_a(test)
	from .. import polynomial

	pd.update()
	fp, proto = pd.factor_by_identifier(t_project_id + '/alt-1')
	test/str(fp) == 'ctx.sub.alt-1'
	test/proto == polynomial.V1

	id, proto2 = pd.identifier_by_factor(fp)
	test/proto2 == proto
	test/id == t_project_id + '/alt-1'

if __name__ == '__main__':
	import sys
	from fault.test import library as libtest
	libtest.execute(sys.modules[__name__])
