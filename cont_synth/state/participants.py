import reflex as rx
from sqlmodel import select
from ..models import Participant, InterviewParticipantLink, Interview, Persona, Product
from .core import ParticipantItem


_PERSONA_COLORS = [
    "red",
    "amber",
    "green",
    "blue",
    "violet",
    "crimson",
]

def _persona_color(name: str) -> str:
    idx = sum(ord(c) for c in name) % len(_PERSONA_COLORS)
    return _PERSONA_COLORS[idx]


class ParticipantStateMixin(rx.State, mixin=True):

    def load_participants(self):
        """Loads participants scoped to the active product workspace."""
        prod_id = int(self.active_product_id)
        with rx.session() as session:
            # All interview IDs for this product
            product_interview_ids = {
                row.id for row in session.exec(
                    select(Interview).where(Interview.product_id == prod_id)
                ).all()
            }

            # Participant IDs that have at least one interview in this product
            product_participant_ids: set[int] = set()
            if product_interview_ids:
                links_in_product = session.exec(
                    select(InterviewParticipantLink).where(
                        InterviewParticipantLink.interview_id.in_(product_interview_ids)
                    )
                ).all()
                product_participant_ids = {lnk.participant_id for lnk in links_in_product}

            # Load participants: prefer product_id filter when set, fall back to interview-link scoping
            all_participants = session.exec(
                select(Participant).order_by(Participant.name)
            ).all()
            relevant = [
                p for p in all_participants
                if (p.product_id == prod_id)
                or (p.product_id is None and p.id in product_participant_ids)
                or (p.product_id is None and p.is_team_member)
            ]

            items: list[ParticipantItem] = []
            for p in relevant:
                # Resolve persona name and colour
                persona_name = ""
                persona_color = "gray"
                if p.persona_id:
                    persona = session.get(Persona, p.persona_id)
                    if persona:
                        persona_name = persona.name
                        persona_color = _persona_color(persona.name)

                # Scope interview count and last date to the active product
                p_links = session.exec(
                    select(InterviewParticipantLink).where(
                        InterviewParticipantLink.participant_id == p.id,
                        InterviewParticipantLink.interview_id.in_(product_interview_ids)
                        if product_interview_ids else False,
                    )
                ).all() if product_interview_ids else []
                interview_count = len(p_links)
                last_date = ""
                if p_links:
                    interview_ids = [lnk.interview_id for lnk in p_links]
                    interviews = session.exec(
                        select(Interview).where(Interview.id.in_(interview_ids))
                    ).all()
                    dated = [
                        iv.interview_date or iv.date_logged.strftime("%Y-%m-%d")
                        for iv in interviews
                    ]
                    last_date = max(dated) if dated else ""

                items.append(ParticipantItem(
                    id=p.id,
                    name=p.name,
                    persona_name=persona_name,
                    persona_color=persona_color,
                    is_team_member=p.is_team_member,
                    segment=p.segment,
                    recruited_via=p.recruited_via,
                    notes=p.notes,
                    interview_count=interview_count,
                    last_interviewed=last_date,
                ))
            self.participants = items

            # Populate autocomplete suggestion lists (scoped to relevant participants)
            personas = session.exec(select(Persona).order_by(Persona.name)).all()
            self.available_personas = [p.name for p in personas]
            self.participant_segments = sorted(
                {p.segment for p in relevant if p.segment}
            )
            self.participant_recruited_vias = sorted(
                {p.recruited_via for p in relevant if p.recruited_via}
            )

    def save_participant(self):
        """Create or update a participant from the current form fields."""
        if self.is_viewer:
            return
        name = self.participant_form_name.strip()
        if not name:
            return
        persona_name = self.participant_form_persona.strip()
        with rx.session() as session:
            # Resolve or create persona if provided
            persona_id = None
            if persona_name:
                persona = session.exec(
                    select(Persona).where(Persona.name == persona_name)
                ).first()
                if not persona:
                    persona = Persona(name=persona_name)
                    session.add(persona)
                    session.commit()
                    session.refresh(persona)
                persona_id = persona.id

            if self.editing_participant_id > 0:
                p = session.get(Participant, self.editing_participant_id)
                if p:
                    p.name = name
                    p.persona_id = persona_id
                    p.is_team_member = self.participant_form_is_team_member
                    p.segment = self.participant_form_segment.strip()
                    p.recruited_via = self.participant_form_recruited_via.strip()
                    p.notes = self.participant_form_notes.strip()
                    session.add(p)
                    session.commit()
            else:
                p = Participant(
                    name=name,
                    persona_id=persona_id,
                    is_team_member=self.participant_form_is_team_member,
                    segment=self.participant_form_segment.strip(),
                    recruited_via=self.participant_form_recruited_via.strip(),
                    notes=self.participant_form_notes.strip(),
                    product_id=int(self.active_product_id),
                )
                session.add(p)
                session.commit()
        self._reset_participant_form()
        self.load_participants()

    def delete_participant(self, participant_id: int):
        """Delete a participant and all their interview links."""
        if self.is_viewer:
            return
        with rx.session() as session:
            links = session.exec(
                select(InterviewParticipantLink).where(
                    InterviewParticipantLink.participant_id == participant_id
                )
            ).all()
            for lnk in links:
                session.delete(lnk)
            p = session.get(Participant, participant_id)
            if p:
                session.delete(p)
            session.commit()
        self.load_participants()

    def start_edit_participant(self, participant_id: int):
        """Pre-fill the form to edit an existing participant."""
        p = next((x for x in self.participants if x.id == participant_id), None)
        if not p:
            return
        self.editing_participant_id = participant_id
        self.participant_form_name = p.name
        self.participant_form_persona = p.persona_name
        self.participant_form_is_team_member = p.is_team_member
        self.participant_form_segment = p.segment
        self.participant_form_recruited_via = p.recruited_via
        self.participant_form_notes = p.notes
        self.is_participant_form_open = True

    def open_add_participant(self):
        """Open the add participant form."""
        self._reset_participant_form()
        self.is_participant_form_open = True

    def cancel_participant_form(self):
        self._reset_participant_form()

    def _reset_participant_form(self):
        self.editing_participant_id = -1
        self.participant_form_name = ""
        self.participant_form_persona = ""
        self.participant_form_is_team_member = False
        self.participant_form_segment = ""
        self.participant_form_recruited_via = ""
        self.participant_form_notes = ""
        self.is_participant_form_open = False
