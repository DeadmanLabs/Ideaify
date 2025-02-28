#!/usr/bin/env python3
"""
Enterprise Idea Summarization System
------------------------------------
A system to process text and audio inputs, summarize business/software ideas,
and store them in Obsidian notes with a focus on extensibility.

Using Langchain and LLM integration for intelligent analysis.
"""

import os
import json
import time
import logging
import subprocess
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import ResponseSchema, StructuredOutputParser  
from langchain.chains import LLMChain


# Load environment variables from .env
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"{datetime.now()} - summarizer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(f"{datetime.now()} - summarizer")

# ==================== DATA MODELS ====================

@dataclass
class IdeaMetadata:
    source_type: str  # e.g. 'audio', 'text_file', 'direct_text', etc.
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

# ==================== INPUT SOURCES ====================

class ContentSource(ABC):
    @abstractmethod
    def get_content(self) -> Dict[str, Any]:
        pass

class TextFileSource(ContentSource):
    def __init__(self, file_path: str):
        self.file_path = file_path
    
    def get_content(self) -> Dict[str, Any]:
        with open(self.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {
            "content": content,
            "metadata": {
                "source_type": "text_file",
                "source_name": os.path.basename(self.file_path),
                "timestamp": datetime.now().isoformat()
            }
        }

class AudioFileSource(ContentSource):
    def __init__(self, file_path: str, whisper_path: str = os.environ.get("WHISPER_PATH", "./whisper.cpp")):
        self.file_path = file_path
        self.whisper_path = whisper_path
    
    def get_content(self) -> Dict[str, Any]:
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Audio file not found: {self.file_path}")
        whisper_exe = os.path.join(self.whisper_path, "main")
        if not os.path.exists(whisper_exe):
            raise FileNotFoundError(f"whisper.cpp executable not found at {whisper_exe}")
        model_path = os.path.join(self.whisper_path, "models/ggml-base.en.bin")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Whisper model not found at {model_path}")
        output_file = f"temp_transcription_{int(time.time())}.txt"
        cmd = [whisper_exe, "-m", model_path, "-f", self.file_path, "-otxt", "-of", output_file]
        logger.info(f"Running transcription command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Transcription failed: {result.stderr}")
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
        os.remove(output_file)
        return {
            "content": content,
            "metadata": {
                "source_type": "audio_file",
                "source_name": os.path.basename(self.file_path),
                "timestamp": datetime.now().isoformat()
            }
        }

class EmailSource(ContentSource):
    def __init__(self, email_path: str):
        self.email_path = email_path
    
    def get_content(self) -> Dict[str, Any]:
        with open(self.email_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {
            "content": content,
            "metadata": {
                "source_type": "email",
                "source_name": os.path.basename(self.email_path),
                "timestamp": datetime.now().isoformat()
            }
        }

class TelegramSource(ContentSource):
    def __init__(self, message_data: Dict[str, Any]):
        self.message_data = message_data
    
    def get_content(self) -> Dict[str, Any]:
        content = self.message_data.get("text", "")
        sender = self.message_data.get("sender", "Unknown")
        timestamp = self.message_data.get("timestamp", datetime.now().isoformat())
        return {
            "content": content,
            "metadata": {
                "source_type": "telegram",
                "source_name": sender,
                "timestamp": timestamp
            }
        }

class DirectTextSource(ContentSource):
    def __init__(self, text: str):
        self.text = text
    def get_content(self) -> Dict[str, Any]:
        return {
            "content": self.text,
            "metadata": {
                "source_type": "direct_text",
                "source_name": "direct_input",
                "timestamp": datetime.now().isoformat()
            }
        }

def create_content_source(source_type: str, **kwargs) -> ContentSource:
    if source_type == "text_file":
        return TextFileSource(kwargs.get("file_path"))
    elif source_type == "audio_file":
        return AudioFileSource(kwargs.get("file_path"))
    elif source_type == "email":
        return EmailSource(kwargs.get("email_path"))
    elif source_type == "telegram":
        return TelegramSource(kwargs.get("message_data", {}))
    elif source_type == "direct_text":
        return DirectTextSource(kwargs.get("text"))
    else:
        raise ValueError(f"Unsupported source type: {source_type}")

# ==================== LLM PROCESSING WITH LANGCHAIN ====================

class LangchainProcessor:
    def __init__(self, config: Dict[str, Any]):
        try:
            self.llm = ChatOpenAI(
                model_name=config.get("openai_model", os.environ.get("OPENAI_MODEL", "gpt-4")),
                temperature=float(config.get("temperature", os.environ.get("TEMPERATURE", 0.7))),
                openai_api_key=config.get("openai_api_key", os.environ.get("OPENAI_API_KEY", ""))
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
{
  "title": "string, concise title (max 60 chars)",
  "summary": "string, comprehensive summary (200-300 words)",
  "key_points": ["string", ...],  // Array of 5-7 key points
  "category": "string, one word category (e.g., software, business)",
  "tags": ["string", ...],         // JSON array of 5-10 tags
  "tech_stack": {
      "frontend": ["string"],
      "backend": ["string"],
      "database": ["string"],
      "infrastructure": ["string"],
      "tools": ["string"]
  },
  "design_philosophy": {
      "principles": ["string"],
      "architecture": ["string"],
      "methodology": ["string"]
  },
  "market_analysis": "string, brief market analysis",
  "risks": ["string", ...]         // Array of potential risks
}

Ensure that your response is valid JSON and follows the schema exactly. Do not include any extraneous text outside of the JSON.

IDEA:
{idea_text}

{format_instructions}
"""
            )
            self.chain = LLMChain(llm=self.llm, prompt=self.prompt_template)
            self.langchain_available = True
            logger.info("Langchain initialized successfully")
        except ImportError as e:
            logger.warning(f"Langchain not available: {e}. Using fallback processor.")
            self.langchain_available = False

    def process(self, text: str) -> Dict[str, Any]:
        if not self.langchain_available:
            return self._fallback_process(text)
        try:
            result = self.chain.run(
                idea_text=text,
                format_instructions=self.format_instructions
            )
            parsed_result = self.parser.parse(result)
            parsed_result = self._process_complex_fields(parsed_result)
            return parsed_result
        except Exception as e:
            logger.error(f"Error processing with Langchain: {e}")
            return self._fallback_process(text)

    def _process_complex_fields(self, result: Dict[str, Any]) -> Dict[str, Any]:
        if "tech_stack" in result and isinstance(result["tech_stack"], str):
            tech_stack = {"frontend": [], "backend": [], "database": [], "infrastructure": [], "tools": []}
            sections = result["tech_stack"].split("\n")
            current_section = None
            for section in sections:
                section = section.strip()
                if not section:
                    continue
                lower_section = section.lower()
                if "frontend" in lower_section:
                    current_section = "frontend"
                elif "backend" in lower_section:
                    current_section = "backend"
                elif "database" in lower_section:
                    current_section = "database"
                elif "infrastructure" in lower_section:
                    current_section = "infrastructure"
                elif "tools" in lower_section:
                    current_section = "tools"
                elif current_section and section.startswith("-"):
                    tech_stack[current_section].append(section.lstrip("- ").strip())
            result["tech_stack"] = tech_stack
        if "design_philosophy" in result and isinstance(result["design_philosophy"], str):
            design_philosophy = {"principles": [], "architecture": [], "methodology": []}
            sections = result["design_philosophy"].split("\n")
            current_section = None
            for section in sections:
                section = section.strip()
                if not section:
                    continue
                lower_section = section.lower()
                if "principles" in lower_section:
                    current_section = "principles"
                elif "architecture" in lower_section:
                    current_section = "architecture"
                elif "methodology" in lower_section:
                    current_section = "methodology"
                elif current_section and section.startswith("-"):
                    design_philosophy[current_section].append(section.lstrip("- ").strip())
            result["design_philosophy"] = design_philosophy
        if "key_points" in result and isinstance(result["key_points"], str):
            key_points = [point.strip().lstrip("-").strip() for point in result["key_points"].split("\n") if point.strip() and not point.strip().lower().startswith(("key points", "features"))]
            result["key_points"] = key_points
        if "risks" in result and isinstance(result["risks"], str):
            risks = [risk.strip().lstrip("-").strip() for risk in result["risks"].split("\n") if risk.strip() and not risk.strip().lower().startswith(("risks", "challenges"))]
            result["risks"] = risks
        if "tags" in result and isinstance(result["tags"], str):
            if "," in result["tags"]:
                tags = [tag.strip() for tag in result["tags"].split(",") if tag.strip()]
            else:
                tags = [tag.strip().lstrip("-").strip() for tag in result["tags"].split("\n") if tag.strip() and not tag.strip().lower().startswith("tags")]
            result["tags"] = tags
        return result

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
            "tech_stack": {
                "frontend": [],
                "backend": [],
                "database": [],
                "infrastructure": [],
                "tools": []
            },
            "design_philosophy": {
                "principles": [],
                "architecture": [],
                "methodology": []
            },
            "market_analysis": "",
            "risks": []
        }

# ==================== STORAGE SYSTEMS ====================

class IdeaStorage(ABC):
    @abstractmethod
    def save_idea(self, idea: Idea) -> bool:
        pass
    
    @abstractmethod
    def get_idea(self, idea_id: str) -> Optional[Idea]:
        pass

class ObsidianVaultStorage(IdeaStorage):
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.ideas_path = self.vault_path / "Ideas"
        self.ideas_path.mkdir(parents=True, exist_ok=True)
        self.index_path = self.ideas_path / "IdeaIndex.md"
        if not self.index_path.exists():
            with open(self.index_path, 'w', encoding='utf-8') as f:
                f.write("# Idea Index\n\n")
                f.write("This file serves as an index of all captured ideas.\n\n")
                f.write("## Recent Ideas\n\n")
    
    def save_idea(self, idea: Idea) -> bool:
        try:
            safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in idea.title)
            safe_title = safe_title.replace(" ", "_")
            filename = f"{idea.id}_{safe_title}.md"
            file_path = self.ideas_path / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(idea.to_markdown())
            with open(self.index_path, 'r', encoding='utf-8') as f:
                index_content = f.read()
            section_marker = "## Recent Ideas\n\n"
            insert_pos = index_content.find(section_marker) + len(section_marker)
            tags_str = ""
            if idea.metadata.tags:
                tags_str = f" #{''.join([f' #{tag}' for tag in idea.metadata.tags])}"
            new_entry = f"- [[{filename.replace('.md', '')}|{idea.title}]] - {idea.metadata.timestamp[:10]} - {idea.category}{tags_str}\n"
            updated_content = index_content[:insert_pos] + new_entry + index_content[insert_pos:]
            with open(self.index_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            logger.info(f"Saved idea to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving idea to Obsidian vault: {e}")
            return False
    
    def get_idea(self, idea_id: str) -> Optional[Idea]:
        matching_files = list(self.ideas_path.glob(f"{idea_id}_*.md"))
        if not matching_files:
            logger.warning(f"No idea found with ID {idea_id}")
            return None
        file_path = matching_files[0]
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            title_line = content.split('\n')[0]
            title = title_line.replace("# ", "") if title_line.startswith("# ") else "Untitled"
            summary_start = content.find("## Summary\n") + len("## Summary\n")
            summary_end = content.find("\n\n", summary_start)
            summary = content[summary_start:summary_end].strip()
            return Idea(
                id=idea_id,
                title=title,
                summary=summary,
                key_points=[],
                category="unknown",
                raw_content="",
                metadata=IdeaMetadata(
                    source_type="unknown",
                    source_name="unknown",
                    timestamp=datetime.now().isoformat()
                )
            )
        except Exception as e:
            logger.error(f"Error retrieving idea {idea_id}: {e}")
            return None

# ==================== MAIN APPLICATION CLASS ====================

class IdeaSummarizer:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.processor = LangchainProcessor(config)
        self.storage = ObsidianVaultStorage(config.get("obsidian_vault_path", "./ObsidianVault"))
    
    def process_input(self, source_type: str, **source_kwargs) -> Optional[Idea]:
        try:
            source = create_content_source(source_type, **source_kwargs)
            content_data = source.get_content()
            raw_content = content_data["content"]
            metadata = IdeaMetadata(**content_data["metadata"])
            logger.info("Processing content with Langchain")
            processed_data = self.processor.process(raw_content)
            if "tags" in processed_data and processed_data["tags"]:
                metadata.tags = processed_data["tags"]
            idea_id = f"idea_{str(uuid.uuid4())[:8]}"
            tech_stack = None
            if "tech_stack" in processed_data and processed_data["tech_stack"]:
                tech_stack_data = processed_data["tech_stack"]
                tech_stack = TechStack(
                    frontend=tech_stack_data.get("frontend", []),
                    backend=tech_stack_data.get("backend", []),
                    database=tech_stack_data.get("database", []),
                    infrastructure=tech_stack_data.get("infrastructure", []),
                    tools=tech_stack_data.get("tools", [])
                )
            design_philosophy = None
            if "design_philosophy" in processed_data and processed_data["design_philosophy"]:
                design_data = processed_data["design_philosophy"]
                design_philosophy = DesignPhilosophy(
                    principles=design_data.get("principles", []),
                    architecture=design_data.get("architecture", []),
                    methodology=design_data.get("methodology", [])
                )
            idea = Idea(
                id=idea_id,
                title=processed_data["title"],
                summary=processed_data["summary"],
                key_points=processed_data["key_points"],
                category=processed_data["category"],
                raw_content=raw_content,
                metadata=metadata,
                tech_stack=tech_stack,
                design_philosophy=design_philosophy,
                market_analysis=processed_data.get("market_analysis"),
                risks=processed_data.get("risks", [])
            )
            if self.storage.save_idea(idea):
                return idea
            return None
        except Exception as e:
            logger.error(f"Error processing input: {e}")
            return None

def load_config() -> Dict[str, Any]:
    default_config = {
        "storage_type": os.environ.get("STORAGE_TYPE", "obsidian"),
        "obsidian_vault_path": os.environ.get("OBS_VAULT_PATH", "./ObsidianVault"),
        "whisper_path": os.environ.get("WHISPER_PATH", "./whisper.cpp"),
        "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
        "openai_model": os.environ.get("OPENAI_MODEL", "gpt-4"),
        "temperature": float(os.environ.get("TEMPERATURE", 0.7))
    }
    return default_config

if __name__ == "__main__":
    config = load_config()
    summarizer = IdeaSummarizer(config)
    # For demonstration purposes, process a direct text input
    example_text = "This is a sample business idea for a next generation idea summarization system that uses Langchain and local transcription with whisper.cpp to generate summaries and store them in an Obsidian vault. Additionally, the system will support VOIP functionalities using pjsua2 for calling or texting a specified number."
    idea = summarizer.process_input("direct_text", text=example_text)
    if idea:
        print("Idea processed and saved successfully!")
        print("Title:", idea.title)
        print("Summary:", idea.summary)
    else:
        print("Failed to process the idea.")
