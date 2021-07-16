"""
# Analyze core data types.
"""
from .. import types as module

def test_Variants(test):
	"""
	# - &module.Variant
	"""
	v = module.Variants('s', 'a', 'i', 'f')
	test/'i' == v.intention
	test/'s' == v.system
	test/'a' == v.architecture
	test/'f' == v.form

	v = module.Variants('s', 'a', 'i')
	test/'i' == v.intention
	test/'s' == v.system
	test/'a' == v.architecture
	test/'' == v.form

	v = module.Variants('s', 'a')
	test/'optimal' == v.intention
	test/'s' == v.system
	test/'a' == v.architecture
	test/'' == v.form

def test_Format(test):
	"""
	# - &module.Format
	"""
	test/module.Format('a', 'b') == module.Format.from_string('a.b')
	test/module.Format('b', 'b') == module.Format.from_string('b.b')

	test/module.Format('c', None) == module.Format.from_string('c')
	test/module.Format('c', None) == module.Format.from_string('c.')
	test/module.Format('c') == module.Format.from_string('c')

def test_Reference_format(test):
	"""
	# - &module.Reference.format
	"""
	r = module.Reference('://project', module.factor@'root', 'type', 'c.kr')
	test/module.Format('c', 'kr') == r.format

def test_FactorPath_constructors(test):
	"""
	# - &module.FactorPath.__matmul__
	"""
	F = module.factor

	s = F@'fault.project.path'
	test/s.absolute == ('fault', 'project', 'path')

	test/(s@'.relative').absolute == ('fault', 'project', 'relative')
	test/(s@'..relative').absolute == ('fault', 'relative')

def test_FactorPath_strings(test):
	"""
	# - &module.FactorPath.__str__
	# - &module.FactorPath.__repr__
	"""
	s = module.factor@'fault.project.path'
	test/str(s) == 'fault.project.path'
	test/repr(s) == "(factor@%r)" %('fault.project.path',)

def test_Reference_isolate(test):
	"""
	# - &module.Reference.isolate
	"""
	r = module.Reference('://project', module.factor@'root', 'i-test', None)
	test/r.isolation == None
	test/r.isolate('replacement').isolation == 'replacement'
	test/r.isolate(None).isolation == None
	test/id(r.isolate(None)) == id(r)

def test_Reference_constructors(test):
	"""
	# - &module.Reference
	"""

	r = module.Reference('project', module.factor@'factor.path')
	test/r.project == 'project'
	test/str(r.factor) == 'factor.path'
	test/r.method == None
	test/r.isolation == None

	ri = module.Reference.from_ri(None, 'project/factor.path')
	test/r == ri

	r = module.Reference('project', module.factor@'factor.path', 'method-id', 'iso')
	test/r.project == 'project'
	test/str(r.factor) == 'factor.path'
	test/r.method == 'method-id'
	test/r.isolation == 'iso'

	ri = module.Reference.from_ri('method-id', 'project/factor.path#iso')
	test/r == ri

if __name__ == '__main__':
	import sys
	from fault.test import library as libtest
	libtest.execute(sys.modules[__name__])
