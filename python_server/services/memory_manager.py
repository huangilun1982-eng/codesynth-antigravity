import os
from pathlib import Path
from datetime import datetime
import re
import asyncio
import subprocess
from utils.logger import server_logger # Import logger

class MemoryManager:
    """
    Manages the 'Memory OS' for CodeSynth.
    Handles reading from SOUL, IDENTITY, USER, MEMORY markdown files,
    and logging interactions.
    """
    def __init__(self, root_path: str = None):
        # Default to user's home directory .gemini/code_synth_memory if not specified
        if root_path:
            self.root_path = Path(root_path)
        else:
            self.root_path = Path.home() / ".gemini" / "code_synth_memory"
        
        self.ensure_structure()

    def ensure_structure(self):
        """Ensures the memory directory and basic files exist."""
        if not self.root_path.exists():
            self.root_path.mkdir(parents=True, exist_ok=True)
            
        logs_dir = self.root_path / "logs"
        if not logs_dir.exists():
            logs_dir.mkdir(exist_ok=True)
            
        # We assume default files (SOUL.md etc) are created by setup or manual injection.
        # If they don't exist, we just won't read them (or could create empty ones).

    def _read_file(self, filename: str) -> str:
        """Reads a markdown file and returns its content. Returns empty string if not found."""
        file_path = self.root_path / filename
        if not file_path.exists():
            return ""
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                # Basic security masking (simple regex for API keys)
                # This is a placeholder for more robust security
                content = re.sub(r"(sk-[a-zA-Z0-9]{48})", "sk-************************", content)
                return content
        except Exception as e:
            server_logger.error(f"Error reading {filename}: {e}")
            return ""

    def get_system_context(self) -> str:
        """
        Assembles the System Prompt from memory files.
        Order: SOUL -> IDENTITY -> MEMORY -> USER
        """
        parts = []
        
        soul = self._read_file("SOUL.md")
        if soul:
            parts.append(f"[SOUL - CORE INSTRUCTIONS]\n{soul}")
            
        identity = self._read_file("IDENTITY.md")
        if identity:
            parts.append(f"[IDENTITY - PERSONA]\n{identity}")
            
        memory = self._read_file("MEMORY.md")
        if memory:
            # Simple truncation for Project Memory to save tokens (Tier L2)
            lines = memory.split('\n')
            if len(lines) > 100:
                memory = '\n'.join(lines[:100]) + "\n... (truncated)"
            parts.append(f"[PROJECT KNOWLEDGE]\n{memory}")
            
        user = self._read_file("USER.md")
        if user:
            parts.append(f"[USER PROFILE]\n{user}")
            
        return "\n\n".join(parts)

    def get_raw_memory(self) -> dict:
        """
        Returns raw content of all memory files for UI display.
        """
        return {
            "soul": self._read_file("SOUL.md"),
            "identity": self._read_file("IDENTITY.md"),
            "user": self._read_file("USER.md"),
            "memory": self._read_file("MEMORY.md")
        }

    def log_interaction(self, user_query: str, ai_response: str):
        """
        Logs the interaction to daily markdown log.
        """
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            log_file = self.root_path / "logs" / f"{today}.md"
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            entry = f"\n\n## [{timestamp}] User\n{user_query}\n\n## [{timestamp}] Assistant\n{ai_response}\n"
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            server_logger.error(f"Error logging interaction: {e}")

    async def condense_memory(self):
        """
        [Advanced] Triggers memory condensation.
        Reads today's logs, invokes LLM to extract key points, and updates USER.md.
        """
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            log_file = self.root_path / "logs" / f"{today}.md"
            
            if not log_file.exists():
                server_logger.info("No logs to condense for today.")
                return

            with open(log_file, "r", encoding="utf-8") as f:
                logs_content = f.read()

            if len(logs_content) < 100:
                server_logger.info("Logs too short to condense.")
                return

            # Avoid circular imports by importing inside method
            from services.llm_client import llm_client

            system_prompt = """
            You are a Memory Assembler for an AI Assistant.
            Your job is to read conversation logs and extract key facts to update the User Profile.
            
            EXTRACT:
            1. User Preferences (language, coding style, frameworks)
            2. Project Key Decisions (architecture, stack)
            3. Future Context (what to do next)
            
            OUTPUT FORMAT:
            - Return ONLY the new facts in bullet point format.
            - If nothing important is found, return "NO_UPDATE".
            - Do not summarize chitchat.
            """

            user_prompt = f"Analyze these logs and extract key memory updates:\n\n{logs_content}"
            
            server_logger.info("🧠 MemoryManager: Condensing memory...")
            # Use async generation to prevent blocking
            summary = await llm_client.generate_async(user_prompt, system=system_prompt)
            
            if "NO_UPDATE" in summary or not summary.strip():
                server_logger.info("🧠 MemoryManager: No important updates found.")
                return

            # Append summary to USER.md
            user_md = self.root_path / "USER.md"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            update_entry = f"\n\n### Learned from {today} (at {timestamp})\n{summary}\n"
            
            with open(user_md, "a", encoding="utf-8") as f:
                f.write(update_entry)
                
            server_logger.info(f"🧠 MemoryManager: Updated USER.md with new insights:\n{summary}")

        except Exception as e:
            server_logger.error(f"Error condensing memory: {e}")

    async def sync_memory(self):
        """
        Syncs the memory repository with remote git using asyncio subprocess.
        """
        try:
            # Check if git is initialized
            if not (self.root_path / ".git").exists():
                return

            async def run_git_async(args):
                process = await asyncio.create_subprocess_exec(
                    "git", *args,
                    cwd=str(self.root_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                if process.returncode != 0:
                    raise Exception(f"Git command failed: {stderr.decode()}")
                return stdout.decode()

            # 1. Pull
            await run_git_async(["pull"])
            
            # 2. Add
            await run_git_async(["add", "."])
            
            # 3. Commit
            status = await run_git_async(["status", "--porcelain"])
            if status.strip():
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                await run_git_async(["commit", "-m", f"Auto-sync: {timestamp}"])
                
                # 4. Push
                await run_git_async(["push"])
                server_logger.info(f"Memory synced at {timestamp}")
            else:
                pass
                
        except Exception as e:
            server_logger.error(f"Sync failed: {e}")

# Singleton instance
memory_manager = MemoryManager()
