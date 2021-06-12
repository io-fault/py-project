"""
# Product directory interface checks.
"""
from ...system import files
from .. import system as module
from ..types import factor, Protocol

t_project_id = 'http://ni.fault.io/test/project'

def setup(pd, local_id='', project='project'):
	pj = (pd/project).fs_mkdir()
	pid = (t_project_id + local_id).encode('utf-8')
	(pj/'.protocol').fs_init(pid + b' factors/polynomial-1')
	return pj

def product_a(test, name='product'):
	td = test.exits.enter_context(files.Path.fs_tmpdir())
	pdr = (td/name).fs_mkdir()

	ctx = (pdr/'ctx').fs_mkdir()
	setup(ctx, '/first-context', project='context')
	sub = (ctx/'sub').fs_mkdir()
	setup(sub, '/second-context', project='context')
	setup(sub, '/alt-1', project='alt-1')
	setup(sub, '/alt-2', project='alt-2')

	para = (pdr/'parallel').fs_mkdir()
	setup(para, '/parallel', project='parallel')
	return td, module.Product(pdr)

def test_Product_attributes(test):
	"""
	# - &module.Product.project_index_route
	# - &module.Product.context_index_route
	"""
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

def test_Project_select_none(test):
	"""
	# - &module.Project.select
	"""
	td, pd = product_a(test)
	pd.update()
	id = t_project_id + '/alt-1'
	fp, proto = pd.factor_by_identifier(id)
	test/str(fp) == 'ctx.sub.alt-1'

	# No factors in alt-1.
	pj = module.Project(pd, t_project_id + '/alt-1', fp, proto({}))
	test/list(pj.select(module.types.factor@"no.such.factor")) == []
	test/list(pj.select(module.types.factor@"")) == []

def test_Project_absolute(test):
	"""
	# - &module.Project.absolute
	"""
	td, pd = product_a(test)
	pd.update()
	id = t_project_id + '/alt-1'
	fp, proto = pd.factor_by_identifier(id)
	test/str(fp) == 'ctx.sub.alt-1'

	pj = module.Project(pd, t_project_id + '/alt-1', fp, proto({}))
	target = t_project_id + '/alt-1'
	test/pj.absolute('.test') == (target, module.types.factor@'test')
	target = t_project_id + '/alt-2'
	test/pj.absolute('..alt-2.test-2') == (target, module.types.factor@'test-2')

	target = t_project_id + '/first-context'
	test/pj.absolute('ctx.context.factor') == (target, module.types.factor@'factor')
	test/pj.absolute('...context.factor') == (target, module.types.factor@'factor')
	test/pj.absolute('....ctx.context.factor') == (target, module.types.factor@'factor')

def test_Project_relative(test):
	"""
	# - &module.Project.relative
	"""
	td, pd = product_a(test)
	pd.update()
	id = t_project_id + '/alt-1'
	fp, proto = pd.factor_by_identifier(id)
	test/str(fp) == 'ctx.sub.alt-1'

	pj = module.Project(pd, t_project_id + '/alt-1', fp, proto({}))
	test/pj.relative('.test') == (fp, module.types.factor@'test')
	test/pj.relative('..alt-2.test-2') == (fp*'alt-2', module.types.factor@'test-2')

	target = module.types.factor@'ctx.context'
	test/pj.relative('ctx.context.factor') == (target, module.types.factor@'factor')
	test/pj.relative('...context.factor') == (target, module.types.factor@'factor')
	test/pj.relative('....ctx.context.factor') == (target, module.types.factor@'factor')

def test_Project_itercontexts(test):
	"""
	# - &module.Project.itercontexts
	"""
	td, pd = product_a(test)
	pd.update()
	id = t_project_id + '/alt-1'
	fp, proto = pd.factor_by_identifier(id)
	test/str(fp) == 'ctx.sub.alt-1'

	pj = module.Project(pd, id, fp, proto({}))
	ctxs = [
		'ctx.sub.context',
		'ctx.context',
	]
	for x, y in zip(pj.itercontexts(), ctxs):
		test/str(x) == y

	# Validate that root is ignored.
	test/len(list(pj.itercontexts())) == 2

def test_Project_image_polynomial(test):
	"""
	# - &module.Project.image
	"""
	td, pd = product_a(test)
	pd.update()
	id = t_project_id + '/alt-1'
	fp, proto = pd.factor_by_identifier(id)
	pj = module.Project(pd, id, fp, proto({}))

	variants = {
		'system': 'nosys',
		'architecture': 'noarch',
	}

	test_int = pj.image(variants, factor@'test')
	test/test_int.absolute[-4:] == ('alt-1', '__f-int__', 'nosys-noarch', 'test.void.i')

	subtest_int = pj.image(variants, factor@'path.subtest')
	test/subtest_int.absolute[-4:] == ('path', '__f-int__', 'nosys-noarch', 'subtest.void.i')

	variants = {
		'system': 'nosys',
		'architecture': 'noarch',
		'intention': 'debug'
	}

	test_int = pj.image(variants, factor@'test')
	test/test_int.absolute[-4:] == ('alt-1', '__f-int__', 'nosys-noarch', 'test.debug.i')

	subtest_int = pj.image(variants, factor@'path.subtest')
	test/subtest_int.absolute[-4:] == ('path', '__f-int__', 'nosys-noarch', 'subtest.debug.i')

def test_Context_import_protocol(test):
	"""
	# - &module.Context.import_protocol
	"""
	ctx = module.Context()
	test.issubclass(ctx.import_protocol('factors/polynomial-1'), module.types.Protocol)

def test_Context_connect(test):
	"""
	# - &module.Context.connect
	"""
	td, pd = product_a(test)
	pd.update()
	pd.store()
	ctx = module.Context()

	ctx_pd = ctx.connect(pd.route)
	test/id(pd) != id(ctx_pd)

	# Check cache retrieval.
	test/id(ctx.connect(pd.route)) == id(ctx_pd)

def test_Context_project(test):
	"""
	# - &module.Context.project
	"""
	td, pd = product_a(test)
	pd.update()
	pd.store()
	ctx = module.Context()

	ctx_pd = ctx.connect(pd.route)
	ctx.load()
	test.isinstance(ctx.project(t_project_id + '/alt-1'), module.Project)
	test.isinstance(ctx.project(t_project_id + '/alt-2'), module.Project)

def test_Context_load(test):
	"""
	# - &module.Context.load
	"""
	td, pd = product_a(test)
	pd.update()
	pd.store()

	ctx = module.Context()
	pd = ctx.connect(pd.route)
	ctx.load()

	id = t_project_id + '/alt-1'
	test/(('project', id) in ctx.instance_cache) == True

	id = t_project_id + '/alt-2'
	test/(('project', id) in ctx.instance_cache) == True

def test_Context_itercontexts(test):
	"""
	# - &module.Context.itercontexts
	"""
	# Same as test_Project_itercontexts, but with Project instances.

	td, pd = product_a(test)
	pd.update()
	pd.store()
	ctx = module.Context()
	pd = ctx.connect(pd.route)
	ctx.load()

	id = t_project_id + '/alt-1'
	pj = ctx.project(id)

	ctxs = [
		'ctx.sub.context',
		'ctx.context',
	]
	for x, y in zip(ctx.itercontexts(pj), ctxs):
		test.isinstance(x, module.Project)
		test/str(x.factor) == y

	# Validate that root is ignored.
	test/len(list(ctx.itercontexts(pj))) == 2

if __name__ == '__main__':
	import sys
	from fault.test import library as libtest
	libtest.execute(sys.modules[__name__])
