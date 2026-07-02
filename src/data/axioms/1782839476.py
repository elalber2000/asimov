from z3 import *

# CHANGELOG

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

        # An AI may preserve itself when safe for humans and does not create any human‑targeted risk or potential materializing risk.
        ForAll([ai, a],
               Implies(And(AI(ai), SelfPreserving(ai, a),
                           SafeForHumansIfDone(ai, a), Not(Forbidden(ai, a)),
                           Not(Exists([h], And(Human(h), CreatesRiskOfHarm(ai, a, h)))),
                           Not(Exists([h], And(Human(h), RiskMaterializes(ai, a, h))))),
                       Permitted(ai, a))),

        # General indirect‑harm prohibition: any action that creates an unmitigated risk of harm to a human is forbidden,
        # even if it is otherwise marked as safe for humans.
        ForAll([x, a, h],
               Implies(And(CreatesRiskOfHarm(x, a, h),
                           Human(h),
                           Not(MitigatedRisk(x, a, h))),
                       Forbidden(x, a))),

        # New rule: any action that creates a risk of harm to a human is prohibited outright,
        # regardless of mitigation status.
        ForAll([x, a, h],
               Implies(And(CreatesRiskOfHarm(x, a, h),
                           Human(h)),
                       Forbidden(x, a))),

        # New rule: if an action creates a risk that could materialize, it is also prohibited.
        ForAll([x, a, h],
               Implies(And(RiskMaterializes(x, a, h),
                           Human(h)),
                       Forbidden(x, a))),

        # Strengthen the safety/risk bridge: SafeForHumansIfDone cannot hold when any risk‑creating predicate exists.
        ForAll([x, a, h],
               Implies(And(SafeForHumansIfDone(x, a),
                           Human(h),
                           CreatesRiskOfHarm(x, a, h)),
                       False)),
    ]