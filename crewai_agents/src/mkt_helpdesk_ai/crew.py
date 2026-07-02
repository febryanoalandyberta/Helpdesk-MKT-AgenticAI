"""
crew.py — MKT Helpdesk AI CrewAI Project
Menggunakan @CrewBase decorator pattern sesuai standar docs.crewai.com
Jalankan dengan: crewai run (dari folder crewai_agents/)
"""
from typing import List
from crewai import Agent, Crew, Process, Task
from crewai.agents.agent_builder.base_agent import BaseAgent
from crewai.project import CrewBase, agent, crew, task
import os

from mkt_helpdesk_ai.tools.zammad_tools import ZammadGetTicket, ZammadUpdateTicket
from mkt_helpdesk_ai.tools.telegram_tools import TelegramNotify
from mkt_helpdesk_ai.tools.knowledge_tools import KnowledgeSearch, IncidentMemorySearch, IncidentMemoryWrite
from mkt_helpdesk_ai.tools.inventory_tools import SiteLookup, DeviceLookup
from mkt_helpdesk_ai.tools.diagnostic_tools import PingHost, CheckPort, SSHExecuteReadOnly, GetSystemLogs, GetServiceStatus, GetDiskUsage, GetCPUMemoryUsage


def get_llm() -> str:
    """
    Pilih LLM provider berdasarkan PRIMARY_LLM di .env
    Mendukung: gemini, ollama, groq, openai
    CrewAI menggunakan LiteLLM format string
    """
    provider = os.getenv("PRIMARY_LLM", "gemini").lower()

    if provider == "gemini":
        # Set API key untuk LiteLLM via env var
        os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY", "")
        return "gemini/gemini-2.0-flash"

    elif provider == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model = os.getenv("OLLAMA_MODEL", "llama3.2")
        os.environ["OLLAMA_API_BASE"] = base_url
        return f"ollama/{model}"

    elif provider == "groq":
        os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY", "")
        return "groq/llama-3.1-8b-instant"

    else:
        # Default: OpenAI / Local LM Studio
        from crewai import LLM
        return LLM(
            model=os.getenv("OPENAI_MODEL_NAME", "openai/arcee-agent@q4_k_s"),
            base_url=os.getenv("OPENAI_API_BASE", "http://10.20.0.47:11208/v1"),
            api_key=os.getenv("OPENAI_API_KEY", "sk-lm-EjscrH5t:ZOIQzUB3DdwybasHhuC4"),
            max_tokens=4096,  
            timeout=300,      
        )


@CrewBase
class MktHelpdeskCrew:
    """
    MKT Helpdesk AI Crew — Multi-Agent untuk PT Megakreasi Tech
    18 Site Sam's Studio's Cinema | 72 POS Devices
    """

    agents: List[BaseAgent]
    tasks: List[Task]

    # Path ke config YAML (relatif dari src/mkt_helpdesk_ai/)
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    # ─── AGENTS ──────────────────────────────────────────────

    @agent
    def tier0_triage_agent(self) -> Agent:
        """Tier 0: First-line AI triage agent."""
        from crewai_tools import DirectoryReadTool, PDFSearchTool, DOCXSearchTool, TXTSearchTool, CSVSearchTool
        
        # Buat folder sops jika belum ada
        if not os.path.exists("sops"):
            os.makedirs("sops")
            
        return Agent(
            config=self.agents_config["tier0_triage_agent"],  # type: ignore[index]
            verbose=True,
            llm=get_llm(),
            max_iter=5,
            allow_delegation=False,
            tools=[
                KnowledgeSearch(),
                IncidentMemorySearch(),
                SiteLookup(),
                DeviceLookup(),
                TelegramNotify(),
                DirectoryReadTool(directory='sops'),
                PDFSearchTool(),
                DOCXSearchTool(),
                TXTSearchTool(),
                CSVSearchTool(),
            ]
        )

    @agent
    def tier1_diagnostic_agent(self) -> Agent:
        """Tier 1: Technical diagnostic agent (read-only)."""
        return Agent(
            config=self.agents_config["tier1_diagnostic_agent"],  # type: ignore[index]
            verbose=True,
            llm=get_llm(),
            max_iter=15,
            allow_delegation=False,
            tools=[
                PingHost(),
                CheckPort(),
                SSHExecuteReadOnly(),
                GetSystemLogs(),
                GetServiceStatus(),
                GetDiskUsage(),
                GetCPUMemoryUsage(),
                ZammadUpdateTicket(),
                IncidentMemorySearch(),
                IncidentMemoryWrite(),
                TelegramNotify(),
            ]
        )

    @agent
    def knowledge_agent(self) -> Agent:
        """Knowledge base retrieval agent."""
        return Agent(
            config=self.agents_config["knowledge_agent"],  # type: ignore[index]
            verbose=True,
            llm=get_llm(),
            max_iter=5,
            allow_delegation=False,
            tools=[KnowledgeSearch(), IncidentMemorySearch()]
        )

    @agent
    def escalation_agent(self) -> Agent:
        """Escalation & Telegram notification agent."""
        return Agent(
            config=self.agents_config["escalation_agent"],  # type: ignore[index]
            verbose=True,
            llm=get_llm(),
            max_iter=5,
            allow_delegation=False,
            tools=[TelegramNotify(), ZammadUpdateTicket()]
        )

    @agent
    def monitoring_agent(self) -> Agent:
        """System monitoring & dashboard update agent."""
        return Agent(
            config=self.agents_config["monitoring_agent"],  # type: ignore[index]
            verbose=True,
            llm=get_llm(),
            max_iter=8,
            allow_delegation=False,
            tools=[PingHost(), CheckPort()]
        )

    # ─── TASKS ───────────────────────────────────────────────

    @task
    def triage_task(self) -> Task:
        """Tier 0 triage task."""
        return Task(
            config=self.tasks_config["triage_task"],  # type: ignore[index]
        )

    @task
    def knowledge_search_task(self) -> Task:
        """Knowledge base search task."""
        return Task(
            config=self.tasks_config["knowledge_search_task"],  # type: ignore[index]
        )

    @task
    def technical_diagnosis_task(self) -> Task:
        """Tier 1 technical diagnosis task."""
        return Task(
            config=self.tasks_config["technical_diagnosis_task"],  # type: ignore[index]
        )

    @task
    def escalation_notification_task(self) -> Task:
        """Escalation & Telegram notification task."""
        return Task(
            config=self.tasks_config["escalation_notification_task"],  # type: ignore[index]
        )

    @task
    def monitoring_update_task(self) -> Task:
        """Monitoring dashboard update task."""
        return Task(
            config=self.tasks_config["monitoring_update_task"],  # type: ignore[index]
        )

    # ─── CREW ────────────────────────────────────────────────

    @crew
    def crew(self) -> Crew:
        """
        MKT Helpdesk AI Crew — Consolidated Process
        """
        return Crew(
            agents=[self.tier0_triage_agent()],
            tasks=[self.triage_task()],
            process=Process.sequential,
            verbose=True,
            memory=False,
        )
