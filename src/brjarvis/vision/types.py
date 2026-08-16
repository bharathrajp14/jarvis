# vision/types.py — Pydantic v2 Data Models for Vision Engine & Semantic UI Graph
from __future__ import annotations

import enum
import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ElementType(str, enum.Enum):
    BUTTON = "BUTTON"
    INPUT = "INPUT"
    TEXT = "TEXT"
    WINDOW = "WINDOW"
    ICON = "ICON"
    UNKNOWN = "UNKNOWN"


class UIRole(str, enum.Enum):
    BUTTON = "button"
    TEXTBOX = "textbox"
    DROPDOWN = "dropdown"
    DIALOG = "dialog"
    TREE = "tree"
    TERMINAL = "terminal"
    EDITOR = "editor"
    BROWSER = "browser"
    WINDOW = "window"
    ICON = "icon"
    TOOLBAR = "toolbar"
    SIDEBAR = "sidebar"
    MENU = "menu"
    TAB = "tab"
    TABLE = "table"
    PROGRESS = "progress"
    NOTIFICATION = "notification"
    UNKNOWN = "unknown"


class ScreenBoundingBox(BaseModel):
    xmin: int
    ymin: int
    xmax: int
    ymax: int

    @property
    def center_x(self) -> int:
        return (self.xmin + self.xmax) // 2

    @property
    def center_y(self) -> int:
        return (self.ymin + self.ymax) // 2

    @property
    def width(self) -> int:
        return max(0, self.xmax - self.xmin)

    @property
    def height(self) -> int:
        return max(0, self.ymax - self.ymin)


class DetectedUIElement(BaseModel):
    element_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    label: str
    text: Optional[str] = None
    bbox: ScreenBoundingBox
    confidence: float = 1.0
    element_type: ElementType = ElementType.UNKNOWN


class SemanticUINode(BaseModel):
    """Semantic UI Node representing a component in the Semantic UI Graph."""
    node_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: UIRole = UIRole.UNKNOWN
    name: str = ""
    value: Optional[str] = None
    parent_id: Optional[str] = None
    children_ids: List[str] = Field(default_factory=list)
    bbox: ScreenBoundingBox = Field(default_factory=lambda: ScreenBoundingBox(xmin=0, ymin=0, xmax=0, ymax=0))
    is_focused: bool = False
    is_enabled: bool = True
    is_clickable: bool = True
    is_editable: bool = False
    confidence: float = 1.0
    source_tier: str = "accessibility"  # accessibility, dom, detection, ocr, vlm


class SemanticUIGraph(BaseModel):
    """Semantic UI Graph representing full hierarchical UI layout."""
    timestamp: float = Field(default_factory=time.time)
    root_id: Optional[str] = None
    nodes: Dict[str, SemanticUINode] = Field(default_factory=dict)
    active_window: Optional[str] = None

    def add_node(self, node: SemanticUINode, parent_id: Optional[str] = None) -> None:
        """Add a node and maintain parent-child links."""
        self.nodes[node.node_id] = node
        if parent_id and parent_id in self.nodes:
            node.parent_id = parent_id
            if node.node_id not in self.nodes[parent_id].children_ids:
                self.nodes[parent_id].children_ids.append(node.node_id)
        if self.root_id is None:
            self.root_id = node.node_id

    def find_by_name(self, name: str) -> List[SemanticUINode]:
        """Search nodes matching name substring (case-insensitive)."""
        name_low = name.lower()
        return [n for n in self.nodes.values() if name_low in n.name.lower() or (n.value and name_low in n.value.lower())]

    def find_by_role(self, role: UIRole) -> List[SemanticUINode]:
        """Find nodes matching specified UIRole."""
        return [n for n in self.nodes.values() if n.role == role]


class ScreenAnalysisReport(BaseModel):
    timestamp: float = Field(default_factory=time.time)
    screen_width: int = 1920
    screen_height: int = 1080
    ocr_text: str = ""
    elements: List[DetectedUIElement] = Field(default_factory=list)
    semantic_graph: Optional[SemanticUIGraph] = None
    frame_hash: int = 0
    active_window_title: Optional[str] = None
