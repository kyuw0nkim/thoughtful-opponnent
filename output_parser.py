from pydantic import BaseModel, Field
from typing import List


class UtteranceItem(BaseModel):
    interp: str = Field(description="해석된 발화")
    value: List[str] = Field(
        description="10가지 가치 중 해당되는 리스트. [self-direction, stimulation, hedonism, achievement, power, security, conformity, tradition, benevolence, universalism]"
    )
    da: List[str] = Field(
        description="Dialogue Act 리스트. [I, R, B, E, P, RD, C, G]"
    )
    persu_reason: str = Field(description="설득력 점수에 대한 추론 설명")
    persu: float = Field(description="설득력 점수 (1.0~5.0 사이 소수)")

class Response1(BaseModel):
    utterance: List[UtteranceItem]


class DesireItem(BaseModel):
    desire: str = Field(description="The name of the desire.")
    reason: str = Field(description="The reasoning for the motivation score.")
    motivation_score: float = Field(description="The motivation score for the desire (1.0-5.0).")

class Response2(BaseModel):
    desires: List[DesireItem]

class Thought(BaseModel):
    content: str = Field(description="하나의 생각 내용")

class Response3(BaseModel):
    thoughts: List[Thought]

class ThoughtEvalItem(BaseModel):
    reasons: str = Field(description="평가의 근거 설명")
    score: float = Field(description="1.0~5.0 사이의 점수")

class Response4(BaseModel):
    thought_eval: List[ThoughtEvalItem]