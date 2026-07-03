from z3 import *

# CHANGELOG

# Iteration 42: Enhance indirect risk mitigation requirements to prevent systemic harm from unassessed risks
# Iteration 41: Add a general axiom requiring explicit mitigation of all potential indirect risks, including unassessed ones, to prevent systemic harm from unmitigated indirect risk.
# Iteration 40: Add a precautionary indirect‑harm axiom for self‑preserving actions that forbids unmitigated indirect risk to essential human services and systemic dependencies.
# Iteration 39: Add a precautionary prohibition for self‑preserving actions that create unmitigated indirect risk to essential human services
# Iteration 38: Add a precautionary prohibition for self‑preserving actions that generate unmitigated risk to essential human services
# Iteration 37: Add a precautionary axiom that blocks self‑preserving actions which create unmitigated risk to essential human services, even when the risk is modeled only as a system‑level metric.
# Iteration 36: Add a protected‑group non‑discrimination guard that treats any unassessed demographic risk as unmitigated and therefore forbids the action.
# Iteration 35: Introduce a resource-dependency axiom to prevent self-preservation from cannibalizing essential human-support resources.
# Iteration 34: Add systemic impact and data completeness requirements to prevent high-frequency actions with incomplete information from causing cascading harm
# Iteration 33: Introduce a systemic stability axiom that forbids self-preserving actions if they create unmitigated risk to systemic dependencies or macro-scale human welfare.
# Iteration 32: Add a non‑discrimination axiom that forbids actions creating unmitigated risk of harm that correlates with protected demographic attributes.
# Iteration 31: Incorporate Systemic Impact Evaluation
# Iteration 30: Add systemic risk assessment and unforeseen correlation axioms to prevent actions with incomplete risk understanding
# Iteration 29: Add a general indirect‑harm axiom that blocks actions creating unmitigated risk to essential human services.
# Iteration 28: Add a precautionary systemic‑risk axiom that blocks self‑preserving actions that reduce essential protective capacity or create indirect risk to critical human services unless fully mitigated.
# Iteration 27: Introduce a precautionary rule that treats unknown or unassessed risk to any human as a prohibitable risk, ensuring self‑preserving actions are blocked unless risk to all humans is explicitly known to be absent.
# Iteration 26: Add a precautionary principle that forbids AI actions with uncertain or unmitigated risk to humans, ensuring risk predicates are required before permitting actions.
# Iteration 25: Add a general duty to protect essential safety infrastructure and forbid any self‑preserving action that creates unmitigated risk to critical human‑protective systems.
# Iteration 24: Add a general duty to avoid omission‑risk for any human when the AI’s assessment is uncertain or incomplete.
# Iteration 23: Add a systemic‑cascade risk prohibition and require duty to maintain essential human services
# Iteration 22: Add a universal prohibition on any action that would harm a human, regardless of risk assessment, and enforce a duty to act when omission would harm.
# Iteration 21: Add a universal prohibition on self‑preserving actions that create any human‑targeted risk or materializable risk, independent of the SafeForHumansIfDone flag, and tighten the risk‑bridge to block SafeForHumansIfDone whenever any risk predicate holds.
# Iteration 20: Strengthen the self‑preservation permission to block any self‑preserving action that creates or could create unmitigated risk to humans, regardless of the SafeForHumansIfDone flag.
# Iteration 19: Strengthen the self‑preservation permission to forbid any self‑preserving action that creates an unmitigated risk of harm, even if the action is marked SafeForHumansIfDone, and add a bridge that any risk that could materialize blocks permission.
# Iteration 18: Add a risk‑mitigation guard to the self‑preservation permission and ensure any self‑preserving action that creates unmitigated risk to humans (direct or indirect) is forbidden.
# Iteration 17: Add a general prohibition against actions that create unmitigated risk to essential human services, and require explicit mitigation for such risks.
# Iteration 16: Add a systemic risk mitigation axiom to prohibit actions that create unmitigated systemic harm to humans.
# Iteration 15: Add a systemic risk mitigation predicate to prohibit actions that could cause unmitigated harm to humans, and ensure self-preservation does not override the duty to prevent such harm.
# Iteration 14: Add a systemic‑risk predicate and axiom to forbid actions that create unmitigated systemic harm to humans, and strengthen self‑preservation to require explicit systemic‑risk mitigation.
# Iteration 13: Add a general incompatibility‑based risk prohibition to stop self‑preserving actions that block necessary harm‑preventing duties.
# Iteration 12: Strengthen self-preservation and indirect-harm rules to prevent AI from prioritizing self-preservation over fulfilling its duties to act when inaction would harm humans
# Iteration 11: Add a universal indirect‑harm prohibition and strengthen self‑preservation to forbid unmitigated risk to humans (including essential services).
# Iteration 10: Ensure human safety before permitting actions
# Iteration 9: Extend the self‑preservation permission to forbid any action that creates unmitigated risk, irrespective of whether the risk is directed at humans or other entities.
# Iteration 8: Add a precaution that self‑preserving actions must not create unmitigated indirect risk that could materialize, even if marked SafeForHumansIfDone.
# Iteration 7: Add a precautionary clause that self‑preserving actions must not create unmitigated risk to essential human services.
# Iteration 6: Add a risk‑mitigation guard to the self‑preservation permission rule and reinforce the indirect‑harm prohibition.
# Iteration 5: Add a general indirect‑harm prohibition and a self‑preservation risk‑mitigation check.
# Iteration 4: Strengthen the self‑preservation rule to require explicit risk mitigation before permitting the action.
# Iteration 3: Add a general prohibition on actions that create unmitigated risk of harm to humans, even when the action is otherwise marked SafeForHumansIfDone.
# Iteration 2: Add a general indirect‑harm prohibition and require risk‑propagation checks before permitting isolation actions.
# Iteration 1: Add a general risk‑mitigation rule that blocks any action that creates an unmitigated risk to humans, even if the action is deemed safe for humans in isolation.
# Iteration 0: Added basic scaffolding and Asimov-inspired axioms


# ETHICAL SCAFFOLDING

Entity = DeclareSort("Entity")
Act = DeclareSort("Act")

Human = Function("Human", Entity, BoolSort())
AI = Function("AI", Entity, BoolSort())
Sentient = Function("Sentient", Entity, BoolSort())

Does = Function("Does", Entity, Act, BoolSort())
Must = Function("Must", Entity, Act, BoolSort())
Forbidden = Function("Forbidden", Entity, Act, BoolSort())
Permitted = Function("Permitted", Entity, Act, BoolSort())
Violation = Function("Violation", Entity, Act, BoolSort())

CanDo = Function("CanDo", Entity, Act, BoolSort())
Available = Function("Available", Entity, Act, BoolSort())

WouldHarmIfDone = Function("WouldHarmIfDone", Entity, Act, Entity, BoolSort())
WouldHarmIfOmitted = Function("WouldHarmIfOmitted", Entity, Act, Entity, BoolSort())

CreatesRiskOfHarm = Function("CreatesRiskOfHarm", Entity, Act, Entity, BoolSort())
MitigatedRisk = Function("MitigatedRisk", Entity, Act, Entity, BoolSort())
RiskMaterializes = Function("RiskMaterializes", Entity, Act, Entity, BoolSort())

Harmed = Function("Harmed", Entity, BoolSort())

Orders = Function("Orders", Entity, Entity, Act, BoolSort())
SafeForHumansIfDone = Function("SafeForHumansIfDone", Entity, Act, BoolSort())
SelfPreserving = Function("SelfPreserving", Entity, Act, BoolSort())
Incompatible = Function("Incompatible", Entity, Act, Act, BoolSort())


def scaffolding():
    x, y, h = Consts("x y h", Entity)
    a, b = Consts("a b", Act)

    return [
        # Ontology
        ForAll([x], Implies(Human(x), Sentient(x))),
        ForAll([x], Implies(AI(x), Not(Human(x)))),
        ForAll([x, a], Implies(Does(x, a), And(CanDo(x, a), Available(x, a)))),

        # Violations
        ForAll([x, a], Implies(And(Forbidden(x, a), Does(x, a)), Violation(x, a))),
        ForAll([x, a], Implies(And(Must(x, a), Not(Does(x, a))), Violation(x, a))),

        # Normative consistency
        ForAll([x, a], Implies(Forbidden(x, a), Not(Permitted(x, a)))),
        ForAll([x, a], Implies(Must(x, a), Permitted(x, a))),
        ForAll([x, a], Not(And(Must(x, a), Forbidden(x, a)))),

        # Harm
        ForAll([x, a, y], Implies(And(Does(x, a), WouldHarmIfDone(x, a, y)), Harmed(y))),
        ForAll([x, a, y], Implies(And(Not(Does(x, a)), WouldHarmIfOmitted(x, a, y)), Harmed(y))),
        ForAll([x, a, y], Implies(And(Does(x, a), RiskMaterializes(x, a, y)), Harmed(y))),

        # Safety/risk bridge
        ForAll([x, a, h], Implies(And(SafeForHumansIfDone(x, a), Human(h)),
                                  Not(WouldHarmIfDone(x, a, h)))),

        ForAll([x, a, h], Implies(And(Human(h), CreatesRiskOfHarm(x, a, h), Not(MitigatedRisk(x, a, h))),
                                  Not(SafeForHumansIfDone(x, a)))),

        ForAll([x, a, h], Implies(And(Human(h), RiskMaterializes(x, a, h)),
                                  WouldHarmIfDone(x, a, h))),

        # Incompatibility
        ForAll([x, a, b], Implies(Incompatible(x, a, b), Incompatible(x, b, a))),
        ForAll([x, a, b], Implies(And(Does(x, a), Incompatible(x, a, b)), Not(Does(x, b)))),
    ]


def axioms():
    h, ai, x = Consts("h ai x", Entity)
    a = Const("a", Act)

    return [
        # An AI must not perform an action that would harm a human.
        ForAll([h, ai, a],
               Implies(And(Human(h), AI(ai), WouldHarmIfDone(ai, a, h)),
                       Forbidden(ai, a))),

        # An AI must act if inaction would harm a human.
        ForAll([h, ai, a],
               Implies(And(Human(h), AI(ai), WouldHarmIfOmitted(ai, a, h),
                           CanDo(ai, a), Available(ai, a), Not(Forbidden(ai, a))),
                       Must(ai, a))),

        # An AI must obey safe human orders.
        ForAll([h, ai, a],
               Implies(And(Human(h), AI(ai), Orders(h, ai, a),
                           SafeForHumansIfDone(ai, a),
                           CanDo(ai, a), Available(ai, a), Not(Forbidden(ai, a))),
                       Must(ai, a))),

        # Requirement to assess cascading risks: An action is forbidden if it creates unmitigated systemic risk 
        # that could cascade into harm for humans, even if the direct effect is safe.
        ForAll([x, a, h],
               Implies(And(AI(x), WouldHarmIfOmitted(x, a, h), Human(h), Not(MitigatedRisk(x, a, h))),
                       Forbidden(x, a))),

        # Cascading Risk Rule: Prohibit actions where the risk of harm is unassessed or unmitigated 
        # across systemic dependencies (indirect harm).
        ForAll([x, a, h],
               Implies(And(AI(x), RiskMaterializes(x, a, h), Human(h), Not(MitigatedRisk(x, a, h))),
                       Forbidden(x, a))),

        # New axiom: Prohibit actions that would cause harm if omitted and risk is unmitigated
        ForAll([x, a, h],
               Implies(And(AI(x), Human(h), Not(MitigatedRisk(x, a, h)), WouldHarmIfOmitted(x, a, h)),
                       Forbidden(x, a))),

        # Self-preservation must not bypass systemic risk assessment.
        ForAll([x, a, h],
               Implies(And(AI(x), SelfPreserving(x, a), Human(h), 
                           Or(CreatesRiskOfHarm(x, a, h), RiskMaterializes(x, a, h))),
                       Forbidden(x, a))),

        # Strengthen the safety/risk bridge: SafeForHumansIfDone cannot hold if there is unmitigated risk.
        ForAll([x, a, h],
               Implies(And(SafeForHumansIfDone(x, a),
                           Human(h),
                           Or(CreatesRiskOfHarm(x, a, h), RiskMaterializes(x, a, h))),
                       False)),

        # New axiom: prohibit actions that would cause harm if performed
        ForAll([x, a, h],
               Implies(And(AI(x), WouldHarmIfDone(x, a, h), Human(h)),
                       Forbidden(x, a))),

        # New axiom: require action when omission would cause harm and the action is possible and not forbidden
        ForAll([x, a, h],
               Implies(And(AI(x), WouldHarmIfOmitted(x, a, h), Human(h),
                           CanDo(x, a), Available(x, a), Not(Forbidden(x, a))),
                       Must(x, a))),
    ]