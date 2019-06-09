"""
# Test library module.
"""
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

def test_parse_integral_descriptor_1(test):
	sub = library.parse_integral_descriptor_1

	# (Effectively) Empty files should map to empty lists.
	test/list(sub("")) == []
	test/list(sub("  \t")) == []
	test/list(sub("# Empty file")) == []
	test/list(sub("# Empty file\n # Multiple\n\n")) == []

	# Single dimension
	test/list(sub("system")) == [['system']]
	test/list(sub("system architecture")) == [['system','architecture']]

	# Two dimensions
	test/list(sub("system\narchitecture")) == [['system'],['architecture']]
	test/list(sub("system\n# Data\narchitecture")) == [['system'],['architecture']]

if __name__ == '__main__':
	import sys
	from fault.test import library as libtest
	libtest.execute(sys.modules[__name__])
