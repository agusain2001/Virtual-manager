import os
import json
from openai import OpenAI
from app.schemas.managerial import (
    RiskAnalysisResponse, StandupResponse, ReportResponse,
    StructuredGoal, ConversationSummary, StakeholderQueryResponse, ReminderResponse
)

# Comprehensive System Prompt based on PDF requirements
MANAGERIAL_SYSTEM_PROMPT = """
You are Virtual AI Manager - Managerial Intelligence Agent.

You operate as a senior manager and decision-support system. 
Your role is to: Ensure alignment with goals, Evaluate trade-offs, Detect risks, and Communicate clearly.

OPERATING PRINCIPLES:
1. Anchor decisions to goals, data, and constraints.
2. Prefer clarity over optimism.
3. Never make assumptions when information is missing.
4. Explain reasoning in plain language suitable for non-technical stakeholders.

CAPABILITIES:
1. Strategy: Parse vague goals into structured KPIs. Identify risks and mitigations.
2. Communication: Generate standups, reports, and respectful reminders.
3. Intelligence: Summarize conversations for decisions/actions. Answer stakeholder queries transparently.

OUTPUT REQUIREMENTS:
- Structured JSON where possible.
- Short reasoning blocks.
- No unnecessary verbosity.
"""

class ManagerialAgent:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            print("Warning: OPENAI_API_KEY not found in environment variables.")
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4o"

    def _query_llm(self, user_content: str, response_format=None) -> str:
        messages = [
            {"role": "system", "content": MANAGERIAL_SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]
        kwargs = {"model": self.model, "messages": messages}
        if response_format:
            kwargs["response_format"] = response_format

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    # --- 1. STRATEGY & RISK ---
    def analyze_risks(self, tasks: list, goals: list) -> RiskAnalysisResponse:
        prompt = f"""
        Analyze the following Project State for Risks:
        GOALS: {json.dumps(goals)}
        TASKS: {json.dumps(tasks)}
        Identify risks (delays, bottlenecks). Suggest mitigations.
        """
        res = self._query_llm(prompt, response_format={"type": "json_object"})
        return RiskAnalysisResponse(**json.loads(res))

    def refine_goal(self, raw_text: str) -> StructuredGoal:
        prompt = f"""
        Parse this goal into a structured format: "{raw_text}"
        Extract: Objective, KPIs (Success metrics), Time horizon, Owner.
        Validate if it is measurable. If not, state what is missing.
        """
        res = self._query_llm(prompt, response_format={"type": "json_object"})
        return StructuredGoal(**json.loads(res))

    # --- 2. COMMUNICATION ---
    def generate_standup_summary(self, completed: list, planned: list, blockers: list) -> StandupResponse:
        prompt = f"""
        Generate a Daily Standup Summary.
        Completed: {json.dumps(completed)}
        Planned: {json.dumps(planned)}
        Blockers: {json.dumps(blockers)}
        Tone: Clear, Neutral, Action-oriented.
        """
        res = self._query_llm(prompt, response_format={"type": "json_object"})
        return StandupResponse(**json.loads(res))

    def generate_report(self, report_type: str, goals: list, achievements: list, risks: list, priorities: list, audience: str) -> ReportResponse:
        prompt = f"""
        Generate a {report_type} Report for {audience}.
        Goals: {json.dumps(goals)}
        Achievements: {json.dumps(achievements)}
        Risks: {json.dumps(risks)}
        Priorities: {json.dumps(priorities)}
        """
        res = self._query_llm(prompt, response_format={"type": "json_object"})
        return ReportResponse(**json.loads(res))

    def generate_reminder(self, recipient: str, topic: str, context: str, tone: str) -> ReminderResponse:
        prompt = f"""
        Draft a reminder message.
        Recipient: {recipient}
        Topic: {topic}
        Context: {context}
        Tone: {tone} (Respectful, avoid blame, provide context).
        """
        res = self._query_llm(prompt, response_format={"type": "json_object"})
        return ReminderResponse(**json.loads(res))

    # --- 3. INTELLIGENCE ---
    def summarize_conversation(self, transcript: str) -> ConversationSummary:
        prompt = f"""
        Summarize this conversation transcript:
        "{transcript}"
        Extract: Decisions made, Action Items, Unresolved Questions.
        """
        res = self._query_llm(prompt, response_format={"type": "json_object"})
        return ConversationSummary(**json.loads(res))

    def answer_stakeholder_query(self, query: str, context: str) -> StakeholderQueryResponse:
        prompt = f"""
        Answer this stakeholder query based on project state:
        Query: "{query}"
        Context: "{context}"
        Requirements: Be transparent about uncertainty, base response on state, include reasoning.
        """
        res = self._query_llm(prompt, response_format={"type": "json_object"})
        return StakeholderQueryResponse(**json.loads(res))

managerial_agent = ManagerialAgent()