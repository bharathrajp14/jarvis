# skills/ — Reusable prompt-template skill system for JARVIS MK37.
"""
Skills are markdown files with YAML frontmatter that define reusable prompt
templates. They can be loaded from multiple sources:
  - Built-in skills (shipped with JARVIS)
  - User-level: ~/.jarvis/skills/*.md
  - Project-level: <cwd>/.jarvis/skills/*.md
  - OpenClaw / Claude / custom skill packs (via skills.installer)

Usage:
    from brjarvis.skills import load_skills, find_skill, execute_skill
"""

from .loader import (  # noqa: F401
    SkillDef,
    load_skills,
    find_skill,
    substitute_arguments,
    register_builtin_skill,
)
from .executor import execute_skill  # noqa: F401

# Alias for list_all_skills
list_all_skills = load_skills

# Importing builtin modules registers all built-in skills
from . import builtin as _builtin  # noqa: F401
from . import builtin_editor as _builtin_editor  # noqa: F401
from . import builtin_extras as _builtin_extras  # noqa: F401
from . import builtin_pro as _builtin_pro  # noqa: F401
from . import builtin_writer as _builtin_writer  # noqa: F401
from . import builtin_rag as _builtin_rag  # noqa: F401

