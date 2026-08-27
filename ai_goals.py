"""
RASTRO — geração de blocos de metas (mensal + 4 semanais + 140 diárias) via IA.

Tenta usar a API da Anthropic (variável de ambiente ANTHROPIC_API_KEY) pra
gerar um bloco personalizado a partir do objetivo/barreira/padrão detectados
no TALK. Se a chave não estiver configurada, ou a chamada falhar por
qualquer motivo (rede, formato de resposta, etc.), cai automaticamente no
gerador baseado em regras (rastro_data.build_full_cycle), pra nunca deixar
o usuário sem metas por causa de uma falha externa.

Em qualquer um dos dois casos, o resultado vira um AIGoalDraft com
status="pendente" — ele só vira metas de verdade pro usuário depois que um
admin aprovar (ver goal_engine.activate_draft).
"""

import json
import os

from rastro_data import PATTERNS, build_full_cycle

ANTHROPIC_MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """Você ajuda a montar um plano de metas para um app de desenvolvimento pessoal chamado RASTRO.
O plano é dividido em:
- 1 meta MENSAL: o objetivo maior e mais complexo do usuário para o mês.
- 4 metas SEMANAIS: desafios intermediários, um pouco mais difíceis que as diárias.
- 140 metas DIÁRIAS: divididas em 4 semanas de 35 (7 dias x 5 metas por dia). Devem ser pequenas, concretas, realizáveis em poucos minutos, e progressivamente construir rumo à meta semanal e depois à mensal.

Regras importantes:
- Nunca sugira nada que pareça diagnóstico médico/psicológico ou substitua ajuda profissional.
- Tom acolhedor, direto, sem cobrança ou culpa.
- As metas diárias de uma semana devem ter alguma progressão de dificuldade ao longo dos 7 dias.
- Responda APENAS com um JSON válido, sem markdown, sem texto antes ou depois, no formato exato:
{"monthly": "texto da meta mensal", "weekly": ["semana 1", "semana 2", "semana 3", "semana 4"], "daily": [["...35 textos da semana 1..."], ["...semana 2..."], ["...semana 3..."], ["...semana 4..."]]}
"""


def _build_user_prompt(objective, barrier, pattern):
    return (
        f"Objetivo detectado no TALK: {objective}\n"
        f"Principal barreira: {barrier}\n"
        f"Padrão observado: {pattern}\n\n"
        "Gere o bloco completo de metas (mensal, 4 semanais, 140 diárias em 4 listas de 35) "
        "seguindo exatamente o formato JSON pedido."
    )


def _call_anthropic(objective, barrier, pattern):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic
    except ImportError:
        return None

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_prompt(objective, barrier, pattern)}],
        )
        text_parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        raw = "".join(text_parts).strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        payload = json.loads(raw)

        # validação mínima do formato antes de aceitar
        if (
            isinstance(payload.get("monthly"), str)
            and isinstance(payload.get("weekly"), list) and len(payload["weekly"]) == 4
            and isinstance(payload.get("daily"), list) and len(payload["daily"]) == 4
            and all(len(week) == 35 for week in payload["daily"])
        ):
            return payload
    except Exception:
        # qualquer falha (rede, JSON malformado, resposta fora do formato) -> cai pro fallback
        return None

    return None


def generate_goal_payload(objective, barrier):
    """Retorna (payload_dict, source) onde source é 'ia' ou 'regra'."""
    pattern = PATTERNS.get(barrier, PATTERNS["não sei por onde começar"])

    payload = _call_anthropic(objective, barrier, pattern)
    if payload is not None:
        return payload, "ia"

    return build_full_cycle(objective, barrier), "regra"
