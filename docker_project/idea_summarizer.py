#!/usr/bin/env python3
"""
Idea Summarization System
-------------------------
A system to process text inputs, summarize business/software ideas,
and store them in Obsidian notes.

Using Langchain and LLM integration for intelligent analysis.
"""

import os
import json
import uuid
import logging
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain_core.runnables import RunnablePassthrough

# Load environment variables from .env
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("idea_summarizer")

# ==================== DATA MODELS ====================

@dataclass
class IdeaMetadata:
    source_type: str  # e.g. 'text_file', 'direct_text', etc.
    source_name: str
    timestamp: str
    tags: List[str] = field(default_factory=list)

@dataclass
class TechStack:
    frontend: List[str] = field(default_factory=list)
    backend: List[str] = field(default_factory=list)
    database: List[str] = field(default_factory=list)
    infrastructure: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    
    def to_markdown(self) -> str:
        md = "## Recommended Tech Stack\n\n"
        sections = [
            ("Frontend", self.frontend),
            ("Backend", self.backend),
            ("Database", self.database),
            ("Infrastructure", self.infrastructure),
            ("Tools", self.tools)
        ]
        for title, items in sections:
            if items:
                md += f"### {title}\n"
                for item in items:
                    md += f"- {item}\n"
                md += "\n"
        return md
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class DesignPhilosophy:
    principles: List[str] = field(default_factory=list)
    architecture: List[str] = field(default_factory=list)
    methodology: List[str] = field(default_factory=list)
    
    def to_markdown(self) -> str:
        md = "## Design Philosophy\n\n"
        sections = [
            ("Principles", self.principles),
            ("Architecture", self.architecture),
            ("Methodology", self.methodology)
        ]
        for title, items in sections:
            if items:
                md += f"### {title}\n"
                for item in items:
                    md += f"- {item}\n"
                md += "\n"
        return md
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class Idea:
    id: str
    title: str
    summary: str
    key_points: List[str]
    category: str
    raw_content: str
    metadata: IdeaMetadata
    tech_stack: Optional[TechStack] = None
    design_philosophy: Optional[DesignPhilosophy] = None
    market_analysis: Optional[str] = None
    risks: Optional[List[str]] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_markdown(self) -> str:
        md = f"# {self.title}\n\n"
        md += f"## Summary\n{self.summary}\n\n"
        md += "## Key Points\n"
        for point in self.key_points:
            md += f"- {point}\n"
        md += "\n"
        if self.tech_stack:
            md += self.tech_stack.to_markdown()
        if self.design_philosophy:
            md += self.design_philosophy.to_markdown()
        if self.market_analysis:
            md += f"## Market Analysis\n{self.market_analysis}\n\n"
        if self.risks:
            md += "## Potential Risks\n"
            for risk in self.risks:
                md += f"- {risk}\n"
            md += "\n"
        md += "## Metadata\n"
        md += f"- **ID**: {self.id}\n"
        md += f"- **Category**: {self.category}\n"
        md += f"- **Source**: {self.metadata.source_type} ({self.metadata.source_name})\n"
        md += f"- **Timestamp**: {self.metadata.timestamp}\n"
        if self.metadata.tags:
            md += f"- **Tags**: {', '.join(self.metadata.tags)}\n"
        md += "\n## Raw Content\n```\n" + self.raw_content + "\n```\n"
        return md

# ==================== INPUT PROCESSING ====================

class TextProcessor:
    """Simple class to process text input"""
    
    def __init__(self, text: str, source_type: str = "direct_text", source_name: str = "direct_input"):
        self.text = text
        self.metadata = {
            "source_type": source_type,
            "source_name": source_name,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_content(self) -> Dict[str, Any]:
        return {
            "content": self.text,
            "metadata": self.metadata
        }

# ==================== LLM PROCESSING WITH LANGCHAIN ====================

class LangchainProcessor:
    def __init__(self):
        try:
            self.llm = ChatOpenAI(
                model_name=os.getenv("OPENAI_MODEL", "gpt-4-turbo"),
                temperature=float(os.getenv("TEMPERATURE", "0.7")),
                openai_api_key=os.getenv("OPENAI_API_KEY")
            )
            self.title_schema = ResponseSchema(
                name="title",
                description="A concise, compelling title for the idea (max 60 chars)"
            )
            self.summary_schema = ResponseSchema(
                name="summary",
                description="A comprehensive summary of the idea (200-300 words)"
            )
            self.key_points_schema = ResponseSchema(
                name="key_points",
                description="5-7 key points or features of the idea as a list"
            )
            self.category_schema = ResponseSchema(
                name="category",
                description="A single category for the idea (e.g., software, business)"
            )
            self.tags_schema = ResponseSchema(
                name="tags",
                description="5-10 relevant tags for the idea as a JSON array of strings."
            )
            self.tech_stack_schema = ResponseSchema(
                name="tech_stack",
                description="Recommended technology stack with sections for frontend, backend, database, infrastructure, and tools"
            )
            self.design_philosophy_schema = ResponseSchema(
                name="design_philosophy",
                description="Recommended design principles, architecture, and methodology"
            )
            self.market_analysis_schema = ResponseSchema(
                name="market_analysis",
                description="Brief analysis of the market potential for this idea"
            )
            self.risks_schema = ResponseSchema(
                name="risks",
                description="List of potential risks or challenges for the idea"
            )
            self.parser = StructuredOutputParser.from_response_schemas([
                self.title_schema,
                self.summary_schema,
                self.key_points_schema,
                self.category_schema,
                self.tags_schema,
                self.tech_stack_schema,
                self.design_philosophy_schema,
                self.market_analysis_schema,
                self.risks_schema
            ])
            self.format_instructions = self.parser.get_format_instructions()
            self.prompt_template = ChatPromptTemplate.from_template(
                """You are an expert business and technology consultant tasked with analyzing ideas and turning them into structured proposals.

Please analyze the following business or software idea and provide a comprehensive breakdown, strictly following the JSON schema provided below.

JSON Schema:
{{
  "title": "string, concise title (max 60 chars)",
  "summary": "string, comprehensive summary (200-300 words)",
  "key_points": ["string", ...],  // Array of 5-7 key points
  "category": "string, one word category (e.g., software, business)",
  "tags": ["string", ...],         // JSON array of 5-10 tags
  "tech_stack": {{
      "frontend": ["string"],
      "backend": ["string"],
      "database": ["string"],
      "infrastructure": ["string"],
      "tools": ["string"]
  }},
  "design_philosophy": {{
      "principles": ["string"],
      "architecture": ["string"],
      "methodology": ["string"]
  }},
  "market_analysis": "string, brief market analysis",
  "risks": ["string", ...]         // Array of potential risks
}}

Ensure that your response is valid JSON and follows the schema exactly. Do not include any extraneous text outside of the JSON.

IDEA:
{idea_text}

{format_instructions}
"""
            )
            # Create a chain that explicitly includes format_instructions
            self.chain = (
                {"idea_text": RunnablePassthrough(), "format_instructions": lambda _: self.format_instructions}
                | self.prompt_template
                | self.llm
                | self.parser
            )
            self.langchain_available = True
            logger.info("Langchain initialized successfully")
        except ImportError as e:
            logger.warning(f"Langchain not available: {e}. Using fallback processor.")
            self.langchain_available = False

    def process(self, text: str) -> Dict[str, Any]:
        if not self.langchain_available:
            return self._fallback_process(text)
        try:
            # Get structured output from LLM
            result = self.chain.invoke({"idea_text": text})
            
            # Convert nested dicts to dataclass instances
            if "tech_stack" in result:
                result["tech_stack"] = TechStack(**result["tech_stack"])
            if "design_philosophy" in result:
                result["design_philosophy"] = DesignPhilosophy(**result["design_philosophy"])
            
            return result
        except Exception as e:
            logger.error(f"Error processing with Langchain: {e}")
            return self._fallback_process(text)

    def _fallback_process(self, text: str) -> Dict[str, Any]:
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        title = lines[0] if lines else "Untitled Idea"
        if len(title) > 60:
            title = title[:57] + "..."
        summary = " ".join(lines[:5]) if len(lines) > 5 else text
        key_points = []
        for line in lines:
            if line.startswith(('-', '*', '•')) or (line[0].isdigit() and line[1:3] in ('. ', ') ')):
                key_points.append(line.lstrip("-*•0123456789.) ").strip())
        if not key_points:
            sentences = text.split('. ')
            key_points = [s.strip() + '.' for s in sentences[:5] if s.strip()]
        return {
            "title": title,
            "summary": summary[:500],
            "key_points": key_points[:7],
            "category": "unknown",
            "tags": [],
            "tech_stack": TechStack(),
            "design_philosophy": DesignPhilosophy(),
            "market_analysis": "",
            "risks": []
        }

# ==================== OBSIDIAN INTEGRATION ====================

class ObsidianExporter:
    def __init__(self, vault_path: str = None):
        # Use OBS_VAULT_PATH from .env if provided, otherwise fall back to OBSIDIAN_VAULT or default
        self.vault_path = vault_path or os.getenv("OBS_VAULT_PATH") or os.getenv("OBSIDIAN_VAULT", "/obsidian/vault")
        
        # Convert relative path to absolute if needed
        if not os.path.isabs(self.vault_path):
            # Get the current working directory
            cwd = os.getcwd()
            self.vault_path = os.path.abspath(os.path.join(cwd, self.vault_path))
            logger.info(f"Converting relative path to absolute: {self.vault_path}")
        
        self.ideas_folder = os.path.join(self.vault_path, "Ideas")
        
        # Ensure the Ideas folder exists
        os.makedirs(self.ideas_folder, exist_ok=True)
        logger.info(f"Obsidian vault path: {self.vault_path}")
        logger.info(f"Ideas folder: {self.ideas_folder}")
    
    def export_idea(self, idea: Idea) -> str:
        """Export an idea to the Obsidian vault as a markdown file"""
        # Create a safe filename
        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in idea.title)
        safe_title = safe_title.replace(" ", "_")
        filename = f"{safe_title}_{idea.id[:8]}.md"
        file_path = os.path.join(self.ideas_folder, filename)
        
        # Write the markdown content
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(idea.to_markdown())
        
        logger.info(f"Exported idea to {file_path}")
        return file_path

# ==================== MAIN FUNCTIONALITY ====================

def process_idea(text: str, source_type: str = "direct_text", source_name: str = "direct_input") -> Idea:
    """Process an idea text and return a structured Idea object"""
    # Process the input
    processor = TextProcessor(text, source_type, source_name)
    content_data = processor.get_content()
    
    # Process with Langchain
    langchain_processor = LangchainProcessor()
    processed = langchain_processor.process(content_data["content"])
    
    # Create metadata
    metadata = IdeaMetadata(
        source_type=content_data["metadata"]["source_type"],
        source_name=content_data["metadata"]["source_name"],
        timestamp=content_data["metadata"]["timestamp"],
        tags=processed.get("tags", [])
    )
    
    # Create and return the Idea object
    return Idea(
        id=str(uuid.uuid4()),
        title=processed["title"],
        summary=processed["summary"],
        key_points=processed["key_points"],
        category=processed["category"],
        raw_content=content_data["content"],
        metadata=metadata,
        tech_stack=processed["tech_stack"],
        design_philosophy=processed["design_philosophy"],
        market_analysis=processed["market_analysis"],
        risks=processed["risks"]
    )

def save_idea_to_obsidian(idea: Idea) -> str:
    """Save an idea to the Obsidian vault"""
    exporter = ObsidianExporter()
    return exporter.export_idea(idea)
