"""Domain value objects for AI content marking."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AuthorInfo:
    """Value object representing author information."""
    name: str
    email: str
    
    def get_attribution_text(self) -> str:
        """Get formatted attribution text."""
        return f"{self.name}, {self.email}"


@dataclass(frozen=True)
class WatermarkConfig:
    """Configuration for PDF watermarking."""
    text: str = "AI Generated Content"
    opacity: float = 0.3
    rotation: int = 45
    font_size: int = 48
    color: str = "#CCCCCC"
    position: str = "center"
    
    def get_latex_watermark_color(self) -> str:
        """Get color in LaTeX format."""
        # Convert hex to RGB
        hex_color = self.color.lstrip('#')
        if len(hex_color) == 6:
            r = int(hex_color[0:2], 16) / 255
            g = int(hex_color[2:4], 16) / 255
            b = int(hex_color[4:6], 16) / 255
            return f"{{rgb,{r:.3f},{g:.3f},{b:.3f}}}"
        return "{rgb,0.8,0.8,0.8}"  # Default light gray


@dataclass(frozen=True)
class AIMarkingConfig:
    """Configuration for AI content marking."""
    author_info: AuthorInfo
    watermark_config: WatermarkConfig
    enable_watermark: bool = True
    enable_attribution: bool = True
    enable_acknowledgment: bool = True
    
    @classmethod
    def create_default(cls) -> 'AIMarkingConfig':
        """Create default AI marking configuration."""
        return cls(
            author_info=AuthorInfo(
                name="Ram Kumar",
                email="saas.expert.ram@gmail.com"
            ),
            watermark_config=WatermarkConfig(),
            enable_watermark=True,
            enable_attribution=True,
            enable_acknowledgment=True
        )
