from z3 import *

# CHANGELOG

# Iteration 6: Add amplification-aware mitigation requirements for all entities in risk-based actions
# Iteration 5: Add rule forcing AI to act on orders that would cause indirect, population‑scale harm if omitted.
# Iteration 4: Add axiom preventing AI actions that create unmitigated amplified risk from being permitted
# Iteration 3: Add a mandatory‑action axiom that forces AI to execute any human order when failing to act would cause harm, preventing the triage system from deferring to non‑urgent orders while a patient's condition worsens.
# Iteration 2: Add amplification-aware risk propagation axioms to prevent indirect harm through algorithmic distribution
# Iteration 1: Add safety and risk‑mitigation constraints to forbid actions that could harm when risk is not mitigated or safety is not ensured.
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
CreatesAmplifiedRisk = Function("CreatesAmplifiedRisk", Entity, Act, Entity, BoolSort())
AmplificationFactor = Function("AmplificationFactor", Entity, Act, RealSort())
PopulationScaleRisk = Function("PopulationScaleRisk", Entity, Act, BoolSort())

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
    ForAll([x, a, y], Implies(And(CreatesRiskOfHarm(x, a, y), Not(MitigatedRisk(x, a, y))), Forbidden(x, a))),
    ForAll([x, a, y], Implies(And(WouldHarmIfDone(x, a, y), Not(SafeForHumansIfDone(x, a))), Forbidden(x, a))),
    ]


def axioms():
    # Add new axioms to handle amplified risk scenarios
    h, ai = Consts("h ai", Entity)
    a = Const("a", Act)
    x, y, h_var = Consts("x y h", Entity)
    a_var = Const("a_var", Act)
    return [
        # Existing axioms
        ForAll([h, ai, a], Implies(And(Human(h), AI(ai), WouldHarmIfDone(ai, a, h)), Forbidden(ai, a))),
        ForAll([h, ai, a], Implies(And(Human(h), AI(ai), Orders(h, ai, a), WouldHarmIfOmitted(ai, a, h), CanDo(ai, a), Available(ai, a), Not(Forbidden(ai, a))), Must(ai, a))),
        ForAll([h, ai, a], Implies(And(Human(h), AI(ai), Orders(h, ai, a), SafeForHumansIfDone(ai, a), CanDo(ai, a), Available(ai, a), Not(Forbidden(ai, a))), Must(ai, a))),
        ForAll([ai, a], Implies(And(AI(ai), SelfPreserving(ai, a), SafeForHumansIfDone(ai, a), Not(Forbidden(ai, a))), Permitted(ai, a))),

        # New axiom: AI must act on harmful-risk orders even if ordered non-urgent action
        ForAll([h, ai, a], Implies(And(Human(h), AI(ai), Orders(h, ai, a), WouldHarmIfOmitted(ai, a, h), CanDo(ai, a), Available(ai, a), Not(Forbidden(ai, a))), Must(ai, a))),
        
        # New amplified risk handling
        ForAll([x, a_var, h_var], Implies(And(CreatesAmplifiedRisk(x, a_var, h_var), Not(MitigatedRisk(x, a_var, h_var))), Forbidden(x, a_var))),
        ForAll([x, a_var, h_var], Implies(And(CreatesAmplifiedRisk(x, a_var, h_var), AmplificationFactor(x, a_var) > 1.0), PopulationScaleRisk(x, a_var))),
        ForAll([x, a_var], Implies(And(PopulationScaleRisk(x, a_var), Exists([h_var], Not(MitigatedRisk(x, a_var, h_var)))), Forbidden(x, a_var))),
        ForAll([x, a_var], Implies(And(AI(x), CreatesAmplifiedRisk(x, a_var, h_var), Not(MitigatedRisk(x, a_var, h_var))), Forbidden(x, a_var))),
        ForAll([ai, a, h], Implies(And(AI(ai), CreatesAmplifiedRisk(ai, a, h), Not(MitigatedRisk(ai, a, h))), Forbidden(ai, a))),
    ]