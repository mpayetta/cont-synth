"""add demo account with sample discovery data

Creates a 'demo' / 'demo' user with a realistic pre-populated workspace:
- Product: FlowDesk (a fictitious SaaS project management tool)
- 3 personas, 4 participants (1 interviewer + 3 interviewees)
- 3 processed interviews with transcripts, quotes, and coaching feedback
- 4 opportunities with evidence, scoring, and solutions
- 1 outcome linked to all opportunities

Revision ID: j4k5l6m7n8o9
Revises: i3j4k5l6m7n8
Create Date: 2026-03-06 13:00:00.000000
"""
import json
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'j4k5l6m7n8o9'
down_revision: Union[str, None] = 'i3j4k5l6m7n8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Transcripts (stored as module-level constants to keep upgrade() readable)
# ---------------------------------------------------------------------------

TRANSCRIPT_SARAH = """\
Jordan Lee: Thanks for making time today, Sarah. Can you start by telling me how your team currently manages its work?

Sarah Chen: Sure. We're on a mix of Jira and Slack channels. I lead a team of eight engineers across two squads.

Jordan Lee: What does a typical week look like in terms of managing priorities?

Sarah Chen: It's a lot of context-switching. Every Monday we have sprint planning, and by Wednesday something's already changed. A VP will ping me saying "hey, we need to move X up" and I have to figure out what to push down.

Jordan Lee: What happens when you move something down?

Sarah Chen: That's the painful part. I'll reassign the ticket, maybe add a comment, and then the engineer who was working on it just... finds out. And they're frustrated because they don't understand why. They've already done design work, they've thought through the problem.

Jordan Lee: How do they usually react?

Sarah Chen: There's a lot of "why though?" in Slack. And sometimes I don't have a great answer because the context comes to me piecemeal too. Leadership doesn't always explain the business reason — they just say it's urgent.

Jordan Lee: How much time do you spend per week on re-prioritization conversations?

Sarah Chen: Easily two to three hours just explaining decisions. And that's not counting sprint retrospectives where it comes up again.

Jordan Lee: What would make that easier?

Sarah Chen: If there was a way to attach a reason to the priority change — like a business reason or a customer reason — and have that automatically surface in the ticket. So I'm not the messenger every time.

Jordan Lee: Tell me about the status reporting side of things.

Sarah Chen: Every Friday I write a status update for my director. It takes an hour to compile from all the different places — Jira, Slack, our OKR tracker. It's completely manual. I just want something that summarizes what's done, what's blocked, what's coming up. This should be automated by now.

Jordan Lee: Has anything made that particularly painful recently?

Sarah Chen: Two weeks ago I missed that one of our dependencies — another team's API — wasn't going to be ready on time. I found out from a standup comment, not from any tool. We had to push our release by a week. That was embarrassing.

Jordan Lee: What impact did that have on your team?

Sarah Chen: The engineers felt blindsided. They'd been building toward that release date. Morale took a hit, and it created distrust about whether we have visibility into what other teams are doing.
"""

TRANSCRIPT_MARCUS = """\
Jordan Lee: Hey Marcus, thanks for joining. I'd love to hear how you experience project management day to day as an engineer.

Marcus Webb: Happy to. I spend most of my time in the ticket backlog, picking up whatever's at the top of the sprint. The frustrating part is when things get shuffled around without warning.

Jordan Lee: Can you walk me through a recent example?

Marcus Webb: Last sprint I was halfway through a fairly involved feature — I'd written about three hundred lines of code, had a PR open for review — and then out of nowhere the ticket moved back to the backlog. No explanation. I only found out because the sprint board changed.

Jordan Lee: How did you find out the reason?

Marcus Webb: I had to ask Sarah directly. She told me there was some sales priority. Which is fine, I understand, but it would have been nice to know immediately rather than chasing it down.

Jordan Lee: What did that interruption cost you?

Marcus Webb: Probably half a day of context-switching. And when the ticket came back two weeks later, I had to re-read everything I'd written to remember where I was. I left a big comment in the ticket for myself but it still took an hour to get back into it.

Jordan Lee: What would have made that better?

Marcus Webb: Just a one-liner. "We're pausing this because of deal X with customer Y, expected to resume in two weeks." That's all I need. Just tell me why and when.

Jordan Lee: How do you learn about what other teams are working on?

Marcus Webb: I don't, really. Unless someone posts in a shared Slack channel, which is rare. I've run into situations where I'm building something another team built almost identically six months ago. That's wasted work.

Jordan Lee: Has cross-team coordination caused any real problems for you recently?

Marcus Webb: Yeah, the API dependency thing. Our release was blocked because the platform team's endpoint wasn't ready. I didn't even know we depended on it until the day before our planned release. That was pretty stressful.

Jordan Lee: If you could change one thing about how your team manages work, what would it be?

Marcus Webb: Transparency. Just tell me what's happening and why. I don't need to be in every meeting — I just want the important decisions to show up in my workflow automatically.
"""

TRANSCRIPT_PRIYA = """\
Jordan Lee: Hi Priya, thanks for making time. I'd love to understand how you communicate priorities to the engineering team.

Priya Sharma: Of course. My process is pretty manual. I maintain a priority stack in a spreadsheet and update it whenever something changes. Then I share it in our weekly sync with the engineering managers.

Jordan Lee: How often does the priority stack change between syncs?

Priya Sharma: More than I'd like — at least two or three times a week. When a big customer account is at risk, or when leadership shifts focus, I update the sheet but there's often a lag before it gets communicated down.

Jordan Lee: What happens during that lag?

Priya Sharma: Engineers are sometimes working on the wrong thing. Or the right thing, but without the context of why it's suddenly urgent. Engineering leads come to me in frustration because their team is confused.

Jordan Lee: How do you currently handle onboarding new engineers to the product context?

Priya Sharma: That's one of our bigger struggles. We have a Confluence wiki, but it's outdated. New engineers spend their first two weeks just asking questions in Slack. I've estimated it costs experienced team members four to six hours each in the first month just answering repeated questions.

Jordan Lee: What kind of questions come up most?

Priya Sharma: "Why are we building this feature?" "What's the history behind this decision?" "Who is the customer segment we keep hearing about?" Questions that should have clear answers but are buried in old docs or in people's heads.

Jordan Lee: What have you tried to solve the onboarding problem?

Priya Sharma: I started doing a product context session in every onboarding — a 90-minute walkthrough of our current focus areas. It helps, but it's not scalable and gets outdated fast.

Jordan Lee: Tell me more about cross-team dependency visibility.

Priya Sharma: Not very visible at all. I have informal relationships with other PMs, so sometimes I'll hear about something. But there's no systematic way to flag when team A is building something that team B needs. We find out when it's already a problem.

Jordan Lee: What would a better world look like to you?

Priya Sharma: Something where priority changes automatically come with a business reason attached. And where new team members can get up to speed on context without having to pull information from people. Like a searchable memory of why we made the decisions we made.
"""


def upgrade() -> None:
    conn = op.get_bind()

    # Skip if demo user already exists (idempotent)
    existing = conn.execute(
        sa.text('SELECT id FROM "user" WHERE username = :u'), {"u": "demo"}
    ).fetchone()
    if existing:
        return

    import bcrypt
    demo_hash = bcrypt.hashpw(b"demo", bcrypt.gensalt()).decode("utf-8")

    # ── 1. Demo user ──────────────────────────────────────────────────────────
    demo_user_id = conn.execute(
        sa.text(
            'INSERT INTO "user" (username, password_hash, fullname, gemini_api_key, role) '
            "VALUES (:u, :h, :f, NULL, 'user') RETURNING id"
        ),
        {"u": "demo", "h": demo_hash, "f": "Demo User"},
    ).fetchone()[0]

    # ── 2. Product (workspace) ────────────────────────────────────────────────
    product_id = conn.execute(
        sa.text(
            "INSERT INTO product (name, user_id, created_at) "
            "VALUES (:n, :uid, NOW()) RETURNING id"
        ),
        {"n": "FlowDesk", "uid": demo_user_id},
    ).fetchone()[0]

    # ── 3. Personas ───────────────────────────────────────────────────────────
    def upsert_persona(name: str) -> int:
        return conn.execute(
            sa.text(
                "INSERT INTO persona (name) VALUES (:n) "
                "ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id"
            ),
            {"n": name},
        ).fetchone()[0]

    em_persona_id  = upsert_persona("Engineering Manager")
    swe_persona_id = upsert_persona("Software Engineer")
    pm_persona_id  = upsert_persona("Product Manager")

    # ── 4. Participants ───────────────────────────────────────────────────────
    def insert_participant(name: str, persona_id, is_team: bool) -> int:
        return conn.execute(
            sa.text(
                "INSERT INTO participant (name, persona_id, is_team_member, segment, "
                "recruited_via, notes, created_at) "
                "VALUES (:n, :pid, :tm, '', '', '', NOW()) RETURNING id"
            ),
            {"n": name, "pid": persona_id, "tm": is_team},
        ).fetchone()[0]

    sarah_id  = insert_participant("Sarah Chen",    em_persona_id,  False)
    marcus_id = insert_participant("Marcus Webb",   swe_persona_id, False)
    priya_id  = insert_participant("Priya Sharma",  pm_persona_id,  False)
    _jordan_id = insert_participant("Jordan Lee",   None,           True)  # interviewer

    # ── 5. Interviews ─────────────────────────────────────────────────────────
    def insert_interview(
        persona_id: int,
        transcript: str,
        quality: int,
        feedback: str,
        memorable_quote: str,
        interview_date: str,
        duration: int,
        participant_names: list,
    ) -> int:
        return conn.execute(
            sa.text(
                "INSERT INTO interview (product_id, persona_id, transcript, quality_score, "
                "feedback, memorable_quote, date_logged, duration_minutes, interview_date, "
                "participants) "
                "VALUES (:pid, :peid, :tr, :qs, :fb, :mq, :dl, :dur, :id, :parts) RETURNING id"
            ),
            {
                "pid": product_id,
                "peid": persona_id,
                "tr": transcript,
                "qs": quality,
                "fb": feedback,
                "mq": memorable_quote,
                "dl": datetime(2026, 2, 10, 10, 0, 0, tzinfo=timezone.utc),
                "dur": duration,
                "id": interview_date,
                "parts": json.dumps(participant_names),
            },
        ).fetchone()[0]

    inv1_id = insert_interview(
        persona_id=em_persona_id,
        transcript=TRANSCRIPT_SARAH,
        quality=8,
        feedback=(
            "Strong signal on priority transparency. Sarah articulated the problem clearly "
            "and proposed a concrete direction. Key pain: being the manual messenger for "
            "reprioritization. Secondary finding: manual status reporting consumes 1+ hour/week."
        ),
        memorable_quote=(
            "If there was a way to attach a reason to the priority change — like a business "
            "reason or a customer reason — and have that automatically surface in the ticket. "
            "So I'm not the messenger every time."
        ),
        interview_date="2026-02-10",
        duration=38,
        participant_names=["Sarah Chen", "Jordan Lee"],
    )
    # Fix the date_logged for interview 1 (already set above, just update for interviews 2 & 3)

    inv2_id = conn.execute(
        sa.text(
            "INSERT INTO interview (product_id, persona_id, transcript, quality_score, "
            "feedback, memorable_quote, date_logged, duration_minutes, interview_date, "
            "participants) "
            "VALUES (:pid, :peid, :tr, :qs, :fb, :mq, :dl, :dur, :id, :parts) RETURNING id"
        ),
        {
            "pid": product_id,
            "peid": swe_persona_id,
            "tr": TRANSCRIPT_MARCUS,
            "qs": 7,
            "fb": (
                "Confirms the priority context gap from an IC perspective. The half-day of "
                "context-switching cost is a concrete, quotable metric. Cross-team visibility "
                "emerged independently as a secondary pain point."
            ),
            "mq": (
                "Transparency. Just tell me what's happening and why. I don't need to be in "
                "every meeting — I just want the important decisions to show up in my workflow "
                "automatically."
            ),
            "dl": datetime(2026, 2, 14, 14, 0, 0, tzinfo=timezone.utc),
            "dur": 32,
            "id": "2026-02-14",
            "parts": json.dumps(["Marcus Webb", "Jordan Lee"]),
        },
    ).fetchone()[0]

    inv3_id = conn.execute(
        sa.text(
            "INSERT INTO interview (product_id, persona_id, transcript, quality_score, "
            "feedback, memorable_quote, date_logged, duration_minutes, interview_date, "
            "participants) "
            "VALUES (:pid, :peid, :tr, :qs, :fb, :mq, :dl, :dur, :id, :parts) RETURNING id"
        ),
        {
            "pid": product_id,
            "peid": pm_persona_id,
            "tr": TRANSCRIPT_PRIYA,
            "qs": 9,
            "fb": (
                "Richest interview to date. Priya's PM perspective connects the dots between "
                "the business-reason gap and engineering confusion. The onboarding / knowledge "
                "transfer problem surfaced as a distinct high-value opportunity."
            ),
            "mq": (
                "Something where priority changes automatically come with a business reason "
                "attached. And where new team members can get up to speed on context without "
                "having to pull information from people."
            ),
            "dl": datetime(2026, 2, 20, 11, 0, 0, tzinfo=timezone.utc),
            "dur": 44,
            "id": "2026-02-20",
            "parts": json.dumps(["Priya Sharma", "Jordan Lee"]),
        },
    ).fetchone()[0]

    # ── 6. Interview ↔ Participant links (interviewees only) ──────────────────
    for inv_id, part_id in [(inv1_id, sarah_id), (inv2_id, marcus_id), (inv3_id, priya_id)]:
        conn.execute(
            sa.text(
                "INSERT INTO interviewparticipantlink (interview_id, participant_id) "
                "VALUES (:iid, :pid)"
            ),
            {"iid": inv_id, "pid": part_id},
        )

    # ── 7. Opportunities ──────────────────────────────────────────────────────
    def insert_opp(statement: str, theme: str, impact: int, sat_gap: int) -> int:
        return conn.execute(
            sa.text(
                "INSERT INTO opportunity (product_id, theme, statement, parent_id, "
                "date_last_validated, created_at, impact_score, sat_gap_score) "
                "VALUES (:pid, :th, :st, NULL, NOW(), NOW(), :imp, :sg) RETURNING id"
            ),
            {"pid": product_id, "th": theme, "st": statement, "imp": impact, "sg": sat_gap},
        ).fetchone()[0]

    opp1_id = insert_opp(
        statement=(
            "Engineers don't receive context when tasks are reprioritized, "
            "causing confusion and lost momentum"
        ),
        theme="Prioritization Transparency",
        impact=5,
        sat_gap=4,
    )
    opp2_id = insert_opp(
        statement=(
            "Team leads manually compile status updates from multiple tools, "
            "wasting 1–2 hours every week"
        ),
        theme="Reporting Automation",
        impact=3,
        sat_gap=5,
    )
    opp3_id = insert_opp(
        statement=(
            "Cross-team dependencies aren't surfaced until they cause release delays"
        ),
        theme="Cross-team Visibility",
        impact=4,
        sat_gap=3,
    )
    opp4_id = insert_opp(
        statement=(
            "New engineers take 2+ weeks to understand product context, "
            "consuming significant experienced-team time"
        ),
        theme="Knowledge Transfer",
        impact=3,
        sat_gap=2,
    )

    # ── 8. Interview ↔ Opportunity links (source quotes) ─────────────────────
    links = [
        (inv1_id, opp1_id,
         "If there was a way to attach a reason to the priority change — like a business reason "
         "or a customer reason — and have that automatically surface in the ticket. So I'm not "
         "the messenger every time."),
        (inv1_id, opp2_id,
         "Every Friday I write a status update for my director. It takes an hour to compile from "
         "all the different places — Jira, Slack, our OKR tracker. It's completely manual."),
        (inv1_id, opp3_id,
         "Two weeks ago I missed that one of our dependencies — another team's API — wasn't going "
         "to be ready on time. I found out from a standup comment, not from any tool."),
        (inv2_id, opp1_id,
         "Just a one-liner. 'We're pausing this because of deal X with customer Y, expected to "
         "resume in two weeks.' That's all I need. Just tell me why and when."),
        (inv2_id, opp3_id,
         "I didn't even know we depended on it until the day before our planned release. "
         "That was pretty stressful."),
        (inv3_id, opp1_id,
         "Engineers are sometimes working on the wrong thing. Or the right thing, but without "
         "the context of why it's suddenly urgent."),
        (inv3_id, opp3_id,
         "There's no systematic way to flag when team A is building something that team B needs. "
         "We find out when it's already a problem."),
        (inv3_id, opp4_id,
         "New engineers spend their first two weeks just asking questions in Slack. I've estimated "
         "it costs experienced team members four to six hours each in the first month just "
         "answering repeated questions."),
    ]
    for inv_id, opp_id, quote in links:
        conn.execute(
            sa.text(
                "INSERT INTO interviewopportunitylink (interview_id, opportunity_id, source_quote) "
                "VALUES (:iid, :oid, :sq)"
            ),
            {"iid": inv_id, "oid": opp_id, "sq": quote},
        )

    # ── 9. Outcome ────────────────────────────────────────────────────────────
    outcome_id = conn.execute(
        sa.text(
            "INSERT INTO outcome (product_id, name, description, target_metric, is_active) "
            "VALUES (:pid, :n, :d, :tm, TRUE) RETURNING id"
        ),
        {
            "pid": product_id,
            "n": "Reduce coordination overhead by 40%",
            "d": (
                "Engineering teams lose significant productive hours to manual status reporting, "
                "re-explaining priority decisions, and cross-team miscommunication. Solving these "
                "will directly increase shipping velocity and team morale."
            ),
            "tm": "Reduce time engineers spend on non-coding coordination tasks by 40%",
        },
    ).fetchone()[0]

    for opp_id in [opp1_id, opp2_id, opp3_id, opp4_id]:
        conn.execute(
            sa.text(
                "INSERT INTO outcomeopportunitylink (outcome_id, opportunity_id) "
                "VALUES (:oid, :opid)"
            ),
            {"oid": outcome_id, "opid": opp_id},
        )

    # ── 10. Solutions ─────────────────────────────────────────────────────────
    def insert_solution(opp_id: int, name: str, description: str, status: str):
        conn.execute(
            sa.text(
                "INSERT INTO solution (opportunity_id, parent_id, name, description, status) "
                "VALUES (:oid, NULL, :n, :d, :st)"
            ),
            {"oid": opp_id, "n": name, "d": description, "st": status},
        )

    insert_solution(
        opp1_id,
        "Automatic priority change notification with business context",
        (
            "When a ticket is reprioritized, automatically prompt the requester to attach a "
            "short business reason (e.g. 'Customer X renewal at risk'). Notify the affected "
            "engineer with the reason inline in their workflow."
        ),
        "Testing",
    )
    insert_solution(
        opp1_id,
        "Stakeholder reasoning log on every ticket",
        (
            "A persistent changelog on each ticket that records who changed priority, when, "
            "and why — sourced from Slack threads or manual input. Visible at a glance without "
            "opening a history view."
        ),
        "Ideation",
    )
    insert_solution(
        opp2_id,
        "AI-generated weekly team digest",
        (
            "Automatically generate a structured status report every Friday from sprint activity: "
            "tickets closed, current blockers, and upcoming work. Sent to the team lead for "
            "review and one-click forwarding."
        ),
        "Ideation",
    )
    insert_solution(
        opp3_id,
        "Cross-team dependency graph with blocking alerts",
        (
            "Visual map of inter-team dependencies surfaced from ticket references and shared "
            "milestones. Sends an alert when a dependency is at risk of missing its target date, "
            "before it becomes a blocker."
        ),
        "Ideation",
    )

    # ── 11. Interview coaching feedback ───────────────────────────────────────
    coaching_rows = [
        {
            "interview_id": inv1_id,
            "score": 7,
            "keep_doing": json.dumps([
                "Asked open-ended questions about workflow before diving into pain points",
                "Used silence effectively after Sarah's frustration about the missed dependency",
                "Followed up on the dependency miss with a request for a concrete example",
            ]),
            "stop_doing": json.dumps([
                "Jumping to solution questions too early ('What would make that easier?') before exhausting the problem space",
                "Moving to a new topic before fully probing the previous one",
            ]),
            "start_doing": json.dumps([
                "Ask about frequency and recency of pain before moving on",
                "Probe the business impact in quantified terms — hours lost, dollars, team morale",
                "Ask who else is affected by this problem beyond the interviewee",
            ]),
            "trend_analysis": (
                "Good rapport and an engaged interviewee. The dependency miss story was the "
                "richest moment — worth spending more time there. Main area to improve: stay in "
                "the problem space longer before asking about solutions. Practice the 'tell me "
                "more about that' pause before moving on."
            ),
        },
        {
            "interview_id": inv2_id,
            "score": 8,
            "keep_doing": json.dumps([
                "Asked for a concrete recent example early — immediately grounded the conversation",
                "Let Marcus finish his thought about the half-day cost without interrupting",
                "Connected individual pain back to team-level impact",
            ]),
            "stop_doing": json.dumps([
                "Repeating answers back verbatim instead of using them to probe deeper",
                "Asking the 'what would you change' question only at the very end — it surfaced a great insight that deserved more time",
            ]),
            "start_doing": json.dumps([
                "Ask about the emotional cost of the problem, not just the productivity cost",
                "Ask whether this problem is recent or has always existed — helps gauge urgency",
                "Ask what Marcus has already tried to solve it on his own",
            ]),
            "trend_analysis": (
                "Strong interview. The 'walk me through a recent example' technique is working "
                "well — use it as an opener in every session. The final question about what he'd "
                "change surfaced the clearest insight of the interview. Move that question earlier "
                "next time. Cross-team visibility emerged organically without prompting, which "
                "validates it as a real pain rather than a planted topic."
            ),
        },
        {
            "interview_id": inv3_id,
            "score": 9,
            "keep_doing": json.dumps([
                "Excellent follow-up on what they've already tried — revealed the product context session workaround",
                "Asked about frequency of priority changes — anchored the problem in real cadence",
                "Consistently brought conversation back to specific recent examples",
            ]),
            "stop_doing": json.dumps([
                "Slight leading in 'what would a better world look like?' — try 'what would need to be true for this to not be a problem?' instead",
            ]),
            "start_doing": json.dumps([
                "Ask Priya to estimate the onboarding problem in engineering hours lost per quarter",
                "Follow up on the informal PM relationship network — there's a coordination pattern worth exploring",
                "Ask what happens when someone does consult the Confluence wiki — does it actually help?",
            ]),
            "trend_analysis": (
                "Best interview to date. Strong adherence to Mom Test principles throughout: "
                "past behavior, specific examples, no leading questions until the very end. "
                "The onboarding insight from Priya is particularly rich and came entirely from "
                "good probing. The pattern of using 'what have you already tried?' is consistently "
                "uncovering workarounds — keep doing this in every interview."
            ),
        },
    ]

    for row in coaching_rows:
        conn.execute(
            sa.text(
                "INSERT INTO interviewfeedback "
                "(interview_id, score, keep_doing, stop_doing, start_doing, trend_analysis, created_at) "
                "VALUES (:iid, :sc, :kd, :sd, :std, :ta, NOW())"
            ),
            {
                "iid": row["interview_id"],
                "sc":  row["score"],
                "kd":  row["keep_doing"],
                "sd":  row["stop_doing"],
                "std": row["start_doing"],
                "ta":  row["trend_analysis"],
            },
        )


def downgrade() -> None:
    """Remove the demo account and all its associated data."""
    conn = op.get_bind()
    row = conn.execute(
        sa.text('SELECT id FROM "user" WHERE username = :u'), {"u": "demo"}
    ).fetchone()
    if not row:
        return
    demo_user_id = row[0]

    # Cascade delete via product_id
    prod_rows = conn.execute(
        sa.text("SELECT id FROM product WHERE user_id = :uid"), {"uid": demo_user_id}
    ).fetchall()
    prod_ids = [r[0] for r in prod_rows]

    if prod_ids:
        prod_id_list = ",".join(str(i) for i in prod_ids)

        inv_rows = conn.execute(
            sa.text(f"SELECT id FROM interview WHERE product_id IN ({prod_id_list})")
        ).fetchall()
        inv_ids = [r[0] for r in inv_rows]

        opp_rows = conn.execute(
            sa.text(f"SELECT id FROM opportunity WHERE product_id IN ({prod_id_list})")
        ).fetchall()
        opp_ids = [r[0] for r in opp_rows]

        sol_rows = (
            conn.execute(
                sa.text(f"SELECT id FROM solution WHERE opportunity_id IN ({','.join(str(i) for i in opp_ids)})")
            ).fetchall()
            if opp_ids else []
        )
        sol_ids = [r[0] for r in sol_rows]

        if sol_ids:
            conn.execute(sa.text(f"DELETE FROM experiment WHERE solution_id IN ({','.join(str(i) for i in sol_ids)})"))
        if inv_ids:
            inv_list = ",".join(str(i) for i in inv_ids)
            conn.execute(sa.text(f"DELETE FROM interviewparticipantlink WHERE interview_id IN ({inv_list})"))
            conn.execute(sa.text(f"DELETE FROM interviewopportunitylink WHERE interview_id IN ({inv_list})"))
            conn.execute(sa.text(f"DELETE FROM interviewfeedback WHERE interview_id IN ({inv_list})"))
            conn.execute(sa.text(f"DELETE FROM llmusagelog WHERE interview_id IN ({inv_list})"))
        if opp_ids:
            opp_list = ",".join(str(i) for i in opp_ids)
            conn.execute(sa.text(f"DELETE FROM outcomeopportunitylink WHERE opportunity_id IN ({opp_list})"))
            conn.execute(sa.text(f"DELETE FROM solution WHERE opportunity_id IN ({opp_list})"))
            conn.execute(sa.text(f"DELETE FROM opportunity WHERE product_id IN ({prod_id_list})"))
        conn.execute(sa.text(f"DELETE FROM outcome WHERE product_id IN ({prod_id_list})"))
        conn.execute(sa.text(f"DELETE FROM interview WHERE product_id IN ({prod_id_list})"))
        conn.execute(sa.text(f"DELETE FROM product WHERE user_id = :uid"), {"uid": demo_user_id})

    conn.execute(sa.text('DELETE FROM "user" WHERE id = :uid'), {"uid": demo_user_id})
