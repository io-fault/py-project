"""
# Test library module.
"""
from ...routes import library as libroutes
from ...system import files
from .. import library

def test_FactorContextPaths(test):
	fr = files.Path.from_absolute(__file__)
	ko = library.identify_filesystem_context(fr)
	fc = library.factorcontext(ko)

	test/fc.project == fr.container.container

def test_factorsegment(test):
	s = library.factorsegment('fault.fake.path')
	test/s.absolute == ('fault', 'fake', 'path')

if __name__ == '__main__':
	import sys
	from fault.test import library as libtest
	libtest.execute(sys.modules[__name__])
