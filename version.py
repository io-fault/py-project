"""
# Release version data structures.
"""
from functools import total_ordering
from dataclasses import dataclass

@dataclass
class Semantic(object):
	"""
	# Primary fields for project using semantic versioning.

	# &Prerelease instances should be carried alongside if such information is desired by a codepath.
	# Separation is performed as any desired comparisions should only use the primary delta fields.

	# [ Properties ]
	# /major/
		# Major revision usually indicating which protocol set is implemented.
		# Often, the API should have intersections with earlier major revisions,
		# but the level of inconsistency is usually high enough to expect mismatches.
	# /minor/
		# Minor revision indicating the level of the protocol set, increasing
		# the number usually indicating an expansion of the protocols.
	# /patch/
		# Revision indicator noting complete protocol set consistency across
		# distinct values. Used for releases that correct defects.

		# Patch should be negative if describing a pre-release and potentially
		# a negative number indirectly identifying the &Prerelease.quality.
	"""

	major: (int) = None
	minor: (int) = None
	patch: (int) = None

	@total_ordering
	def __gt__(self, operand):
		return (self.major, self.minor, self.patch) > (operand.major, operand.minor, operand.patch)

@dataclass
class Prerelease(object):
	"""
	# Pre-release version information.

	# [ Properties ]
	# /quality/
		# A string describing the quality of the release.
		# For example, `'beta'`, `'alpha'`, `'rc'`.
	# /serial/
		# An integer incremented to distinguish from previous pre-releases with the same quality.
	"""

	quality: (str) = None
	serial: (int) = None
