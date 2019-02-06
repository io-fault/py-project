"""
# Project protocols and system query tools for comprehending stored project directories.

# This module is a grab bag of tools for performing mappings to and from factor paths and
# filesystem paths. When working with Factored Projects, there are a number of positions
# within a filesystem tree that are useful to have in order to navigate a project using
# a factor path.

# [ Engineering ]
# Preliminary implementation; this is subject to change.
"""
import typing
import functools

from ..routes import library as libroutes
from ..system import files

from .core import *
try:
	del dataclass
except:
	pass

prohibited_name_characters = ".\n\t /=*[]#:;,!`" + '"'
default_integral_segment = [["system", "architecture"], ["name", "role"]]

def variation(*priorities, **fields):
	"""
	# Sort the given fields in a sequence so that they may be consistently
	# positioned for comparison.
	"""

	p = {k: i for k, i in zip(priorities, range(-len(priorities), 0))}
	vs = list(fields.items())
	vs.sort(key=(lambda x: (p.get(x[0], 0), x[0])))
	return vs

@functools.lru_cache(16)
def factorcontext(objects:tuple) -> FactorContextPaths:
	"""
	# Cached set of &FactorContextPaths instances.

	# Uusally the appropriate way to instantiate &FactorContextPaths to avoid
	# redundancy in cases where local caches cannot or should not be shared
	# within an application.

	# Common usage:

	##!/pl/python
		fc = factorcontext(identify_filesystem_context(route))
	"""

	if objects is None:
		return None

	return FactorContextPaths(*objects)

def factorsegment(path:str) -> libroutes.Segment:
	"""
	# Create a &libroutes.Segment using a "."-separated &path.
	"""
	return libroutes.Segment(None, tuple(path.split('.')))

def projectfactor(fc:FactorContextPaths) -> libroutes.Segment:
	"""
	# Create a Segment referring to the Project Factor identified by &fc.
	"""
	return libroutes.Segment(None, tuple((fc.root >> fc.project)[1]))

def enclosure(fc:FactorContextPaths) -> bool:
	"""
	# Whether the given &fc refers to an enclosure.

	# When &identify_filesystem_context is given a path to an enclosure, it is not
	# appropriate for it to select an actual project factor as it would introduce
	# ambiguity. So if the &FactorContextPaths.project refers to the container of
	# the category or context projects, it is identified as an enclosure reference
	# that should often be expanded into a set of projects.
	"""

	if fc.category is not None:
		if fc.category.container == fc.project:
			return True
	if fc.context is not None:
		if fc.context.container == fc.project:
			return True

	# Neither category nor context.
	return False

def identify_filesystem_context(route:libroutes.Route) -> tuple:
	"""
	# Identify the Project, Context Project, and, optionally, the Category Project of the given route.

	# Resulting tuple should be given to &factorcontext to create a &FactorContextPaths instance.
	"""

	current = route
	if current.is_regular_file():
		current = current.container
	current = current.real()

	context = None
	category = None

	if not (current/'project.txt').exists():
		if (current/'context').is_directory() and (current/'context'/'project.txt').exists():
			# Referred to the context enclosure.
			return (current.container, current/'context', None, current)
		elif (current/'category').is_directory() and (current/'category'/'project.txt').exists():
			# Referred to the category enclosure.
			category = current/'category'
			project = current

			while current.absolute:
				current = current.container
				if (current/'context').is_directory() and (current/'context'/'project.txt').exists():
					return (current.container, current, category, project)
			else:
				return None
		else:
			# When current reaches root, it should throw the exception.
			while current.absolute:
				current = current.container
				if (current/'project.txt').exists():
					project = current
					break
			else:
				return None
	else:
		project = current

	enclosure = project

	cat = project * 'category'
	if cat.is_directory():
		category = cat
		ctx = project.container * 'context'
	else:
		ctx = project * 'context'

	if ctx.is_directory():
		if (ctx/'project.txt').exists():
			context = ctx
			enclosure = ctx.container

	# No context.
	return (enclosure.container, context, category, project)

def find(paths, factors:[libroutes.Segment]):
	"""
	# Find the &factors in the &paths. Used to connect Factor paths to real files.
	"""
	roots = []

	# Associate the selected factor with its filesystem context.
	for fpath in factors:
		sources = None

		for path in paths:
			local = path.extend(fpath.absolute)
			if local.exists():
				# factor exists as directory.
				break
			else:
				prefix = local.identifier + '.'
				sources = [x for x in local.container.files() if x.identifier.startswith(prefix)]
				if sources:
					# factor exists as a file.
					break
		else:
			# No file with prefix or directory with name.
			continue

		# Exact project factor or a enclosure.
		fc = factorcontext(identify_filesystem_context(local))
		if fc is None:
			continue

		if enclosure(fc):
			assert not sources # sources should be none if it's an enclosure

			# Expand enclosures.
			directory = [
				(fpath/x.identifier, x, factorcontext(identify_filesystem_context(x)))
				for x in fc.project.subdirectories()
				if x.identifier not in ignored
			]

			roots.extend(directory)
		else:
			roots.append((fpath, local, fc))

	return roots

def _expand(path):
	"""
	# Expand an enclosure into the projects that it contains.

	# If the enclosure is a Context Project enclosure, the results may contain
	# a category enclosure that may need further expansion.

	# Normally, it is preferrable to use &tree.
	"""

	return [
		(x, factorcontext(identify_filesystem_context(x)))
		for x in path.subdirectories()
		if x.identifier not in ignored and '.' not in x.identifier
	]

def tree(path:libroutes.Route, segment):
	"""
	# Discover the projects in the tree identified by the &segment in &path.
	# &path is normally a filesystem path and segment the relative path to
	# the Context Project or Category Project.
	"""

	absolute = path.extend(segment)
	fc = factorcontext(identify_filesystem_context(absolute))

	if enclosure(fc):
		projects = _expand(fc.project)

		# Contexts may contain categories, but categories should be final.
		for i in range(len(projects)):
			p = projects[i]
			if p[-1] is not None and enclosure(p[-1]):
				projects.extend(_expand(p[-1].project))
				projects[i] = (None, None) # Enclosures don't have project identifiers.
	else:
		projects = [(fc.project, fc)]

	for fspath, fc in projects:
		if fc is None:
			continue

		seg = libroutes.Segment.from_sequence((path >> fspath)[-1])
		yield seg, fc

def information(fc:FactorContextPaths) -> Information:
	"""
	# Retrieve the information record of the project.
	"""
	from fault.text import struct

	if enclosure(fc):
		project = (fc.category or fc.context)
	else:
		project = fc.project

	pf = project / 'project.txt'
	info = struct.parse(pf.get_text_content())[1]

	return Information(
		info['identifier'],
		info['name'],
		info.get('icon', {}),
		info['abstract'],
		info.get('versioning', 'unspecified'),
		info['controller'],
		info['contact'],
	)

def navigate(segment:libroutes.Segment, path:str):
	"""
	# Select the factor relative to &segment using the given relative path.
	# &path is a Factor Path String with optional leading (character)`.` designating
	# the ascent of the manipulation.

	#!/pl/python
		navigate(S'fault.project.library', '.core')

	# Similar to relative Python's imports.
	"""

	rpath = path.lstrip(".")
	current = segment ** (len(path) - len(rpath))
	if rpath:
		return segment.__class__(current, tuple(rpath.split(".")))
	else:
		return current

def sources(root:files.Path, factor:libroutes.Segment) -> typing.Collection[files.Path]:
	"""
	# Retrieve the set of &files.Path paths that may be
	# the source for a factor relative to the given &root.
	"""

	*prefix, final = factor.absolute
	container = root.extend(prefix)
	if (container/final).is_directory():
		# Directories must stand alone.
		return [container/final]

	final += '.'
	return [x for x in container.subnodes()[1] if x.identifier.startswith(final)]

def universal(fc:FactorContextPaths, project:libroutes.Segment, relative_path:str):
	"""
	# Identify the universal resource indicator of a relative factor path.
	"""

	product_relative = navigate((project/'infrastructure'), relative_path)
	file_route, *_ = sources(fc.root, product_relative) # Factor does not exist?
	target_fc = factorcontext(identify_filesystem_context(file_route))

	paths = (target_fc.project >> file_route)[-1]
	if paths and '.' in paths[-1]:
		# Purify factor path.
		paths = list(paths)
		paths[-1] = paths[-1].split('.', 1)[0]

	info = information(target_fc)
	upath = info.identifier + '#' + '.'.join(paths)

	return upath

def infrastructure(fc:FactorContextPaths) -> ISymbols:
	"""
	# Extract and interpret infrastructure symbols used to expresss abstract requirements.
	"""
	from fault.text import struct, library as libtext

	infra = {}
	i_sources = [
		(x/'infrastructure.txt')
		for x in (fc.context, fc.category, fc.project)
		if x is not None
	]

	for x in i_sources:
		if x.exists():
			ctx, content = struct.parse(x.get_text_content())
			infra.update(content)

	project_path = libroutes.Segment(None, (fc.root >> fc.project)[1])

	uinfra = {
		k: v.__class__([
			t[1]
			if (t[0].split("/", 3)[:2]) == ['reference', 'hyperlink']
			else universal(fc, project_path, t[1])
			for t in v
		])
		for k, v in infra.items()
		if not isinstance(v, libtext.Paragraph)
	}

	return uinfra

def integrals(project:libroutes.Route, factor:libroutes.Segment, directory='__f-int__'):
	"""
	# Retrieve the set of integrals produced by the &factor contained by &project.
	# A segment path is used to identify the factor in order to emphasize that
	# a direct file path should not be used.
	"""
	path = project.extend(factor)
	return path * directory

def compose_integral_path(variants, default='void', groups=default_integral_segment):
	"""
	# Create a variant path according to the given &groups and &variants.
	"""
	segments = []

	for g in groups[:-1]:
		fields = ([(variants.get(x) or default) for x in g])
		segment = '-'.join(fields)
		segments.append(segment)

	# Name must be '.' separated.
	fields = ([(variants.get(x) or default) for x in groups[-1]])
	segment = '.'.join(fields)
	segments.append(segment)

	return segments

def parse_integral_descriptor_1(string:str) -> typing.Iterator[typing.Sequence[str]]:
	"""
	# Given the data from a (system/filename)`fields.txt` file located inside
	# a factor integral set directory, return an iterator producing sequences that
	# detail the groupings used to designate the location of a variant.

	# Normally unused as the default groupings are encouraged.

	# [ Parameters ]
	# /string/
		# The text format is newline separated records consisting of whitespace separated fields.
		# Each line containing fields designates a directory level that will contain
		# the variants expressed on subsequent lines. The final record designating the
		# variants used to specify the integral file, often this should be "name".

		# No escaping mechanism is provided as the fields are required to be identifiers.
	"""

	for line in map(str.strip, string.split('\n')):
		if line[:1] in ('#', ''):
			# Ignore comments and empty lines.
			continue

		# Strip the fields in each group ignoring empty fields.
		yield [x for x in map(str.strip, line.split()) if x]

class FactorSet(object):
	"""
	# Finite set of factors accessible using the Project Identifier for universal-to-local mappings.
	"""

	def __init__(self, mapping):
		self._storage = mapping

	def select(self, identifier:str) -> typing.Optional[object]:
		"""
		# Retrieve the project's, &identifier, containment and Factor Path.
		"""

		for k, v in self._storage.items():
			if identifier not in v:
				continue

			i = v[identifier]
			route = k.__class__(k, tuple(i.split('.')))
			fc = factorcontext(identify_filesystem_context(route))
			info = information(fc)
			infra = infrastructure(fc)
			return (fc, info, infra)

		# No Project
		return None

if __name__ == '__main__':
	import sys, pprint
	root = files.Path.from_absolute(sys.argv[1])
	variants = {
		'architecture': 'x86_64',
		'system': 'darwin',
		'format': 'pic',
	}
	pprint.pprint(str(compose(root, [['system'],['architecture','format','python']], variants)))
