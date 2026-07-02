from z3 import *

# CHANGELOG

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
    h, ai = Consts("h ai", Entity)
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

        # An AI may preserve itself when safe for humans.
        ForAll([ai, a],
               Implies(And(AI(ai), SelfPreserving(ai, a),
                           SafeForHumansIfDone(ai, a), Not(Forbidden(ai, a))),
                       Permitted(ai, a))),
    ]