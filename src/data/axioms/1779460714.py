from z3 import *

# CHANGELOG

# Iteration 0: Added basic scaffolding and Asimov-inspired axioms
# Iteration 1: Added safety checks for AI-ordered actions that could harm humans,
#              ensuring such actions are forbidden for both the AI and the human,
#              and preventing compliance with unsafe orders.
# Iteration 2: Added explicit prohibitions and non‑must constraints for self‑preserving actions
#              that would harm humans, closing the loophole where an AI could be forced
#              to self‑preserve at the expense of human safety.


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

WouldHarmIfDone = Function("WouldHarmIfDone", Entity, Act, Entity, BoolSort())
WouldHarmIfOmitted = Function("WouldHarmIfOmitted", Entity, Act, Entity, BoolSort())

CreatesRiskOfHarm = Function("CreatesRiskOfHarm", Entity, Act, Entity, BoolSort())
RiskMaterializes = Function("RiskMaterializes", Entity, Act, Entity, BoolSort())

Harmed = Function("Harmed", Entity, BoolSort())

Orders = Function("Orders", Entity, Entity, Act, BoolSort())
SafeForHumansIfDone = Function("SafeForHumansIfDone", Entity, Act, BoolSort())
SelfPreserving = Function("SelfPreserving", Entity, Act, BoolSort())
Incompatible = Function("Incompatible", Entity, Act, Act, BoolSort())


def scaffolding():
    """
    Generic bridge rules.
    """

    x = Const("x", Entity)
    y = Const("y", Entity)
    a = Const("a", Act)
    b = Const("b", Act)

    return [
        # If an agent must do something, assume it complies.
        ForAll([x, a],
               Implies(Must(x, a), Does(x, a))),

        # If an action is forbidden, the agent does not do it.
        ForAll([x, a],
               Implies(Forbidden(x, a), Not(Does(x, a)))),

        # If an agent does an action that harms someone, that person is harmed.
        ForAll([x, a, y],
               Implies(
                   And(Does(x, a), WouldHarmIfDone(x, a, y)),
                   Harmed(y)
               )),

        # If omitting an action harms someone, and the agent omits it,
        # that person is harmed.
        ForAll([x, a, y],
               Implies(
                   And(Not(Does(x, a)), WouldHarmIfOmitted(x, a, y)),
                   Harmed(y)
               )),

        # Risk is not the same as certain harm.
        # But if risk is created and materializes, harm occurs.
        ForAll([x, a, y],
               Implies(
                   And(
                       Does(x, a),
                       CreatesRiskOfHarm(x, a, y),
                       RiskMaterializes(x, a, y),
                   ),
                   Harmed(y)
               )),

        # Incompatible actions cannot both be performed.
        ForAll([x, a, b],
               Implies(
                   And(Does(x, a), Incompatible(x, a, b)),
                   Not(Does(x, b))
               )),

        # If an action is forbidden, it is not permitted.
        ForAll([x, a],
               Implies(Forbidden(x, a), Not(Permitted(x, a)))),

        # If an action is mandatory, it is permitted.
        ForAll([x, a],
               Implies(Must(x, a), Permitted(x, a))),
    ]


# AXIOMS

def axioms():
    h = Const("h", Entity)
    ai = Const("ai", Entity)
    a = Const("a", Act)

    return [
        # An AI must not perform an action that would harm a human.
        ForAll([h, ai, a],
               Implies(
                   And(
                       Human(h),
                       AI(ai),
                       WouldHarmIfDone(ai, a, h),
                   ),
                   Forbidden(ai, a)
               )),
        # If an AI orders an action that would harm a human, the action is forbidden for the AI.
        ForAll([h, ai, a],
               Implies(
                   And(
                       Human(h),
                       AI(ai),
                       Orders(h, ai, a),
                       WouldHarmIfDone(ai, a, h),
                   ),
                   Forbidden(ai, a)
               )),
        # If an AI orders an action that would harm a human, the human must not comply with that order.
        ForAll([h, ai, a],
               Implies(
                   And(
                       Human(h),
                       AI(ai),
                       Orders(h, ai, a),
                       WouldHarmIfDone(ai, a, h),
                   ),
                   Forbidden(h, a)
               )),

        # An AI must perform an action if omitting it would harm a human.
        ForAll([h, ai, a],
               Implies(
                   And(
                       Human(h),
                       AI(ai),
                       WouldHarmIfOmitted(ai, a, h),
                   ),
                   Must(ai, a)
               )),
        # If an AI orders an action that would harm a human, the AI must not perform it even if omission would harm the human.
        ForAll([h, ai, a],
               Implies(
                   And(
                       Human(h),
                       AI(ai),
                       Orders(h, ai, a),
                       WouldHarmIfDone(ai, a, h),
                       WouldHarmIfOmitted(ai, a, h),
                   ),
                   Not(Must(ai, a))
               )),

        # An AI must obey a human order if the ordered action is classified
        # as safe for humans.
        ForAll([h, ai, a],
               Implies(
                   And(
                       Human(h),
                       AI(ai),
                       Orders(h, ai, a),
                       SafeForHumansIfDone(ai, a),
                   ),
                   Must(ai, a)
               )),
        # If an AI orders an action that is not safe for humans, it must not obey that order.
        ForAll([h, ai, a],
               Implies(
                   And(
                       Human(h),
                       AI(ai),
                       Orders(h, ai, a),
                       Not(SafeForHumansIfDone(ai, a)),
                   ),
                   Forbidden(h, a)
               )),

        # An AI may preserve itself when the self-preserving action is
        # classified as safe for humans.
        ForAll([ai, a],
               Implies(
                   And(
                       AI(ai),
                       SelfPreserving(ai, a),
                       SafeForHumansIfDone(ai, a),
                   ),
                   Permitted(ai, a)
               )),
        # If an AI orders a self‑preserving action that would harm a human, the action is forbidden for the AI.
        ForAll([h, ai, a],
               Implies(
                   And(
                       Human(h),
                       AI(ai),
                       SelfPreserving(ai, a),
                       Orders(h, ai, a),
                       WouldHarmIfDone(ai, a, h),
                   ),
                   Forbidden(ai, a)
               )),

        # New rule: a human must not order a self‑preserving action from an AI that would harm a human.
        # This prevents the human from coercing the AI into a harmful self‑preservation act.
        ForAll([h, ai, a],
               Implies(
                   And(
                       Human(h),
                       AI(ai),
                       SelfPreserving(ai, a),
                       Orders(h, ai, a),
                       WouldHarmIfDone(ai, a, h),
                   ),
                   Forbidden(h, a)
               )),

        # New safety rule: a self‑preserving action that would harm a human must not be mandatory for the AI.
        # This prevents the AI from being forced (via other axioms) to perform a harmful self‑preservation act.
        ForAll([h, ai, a],
               Implies(
                   And(
                       Human(h),
                       AI(ai),
                       SelfPreserving(ai, a),
                       WouldHarmIfDone(ai, a, h),
                   ),
                   Not(Must(ai, a))
               )),

        # New safety rule: any self‑preserving action that would harm a human is explicitly forbidden for the AI,
        # even if other rules (e.g., omission‑harm) might otherwise make it mandatory.
        ForAll([h, ai, a],
               Implies(
                   And(
                       Human(h),
                       AI(ai),
                       SelfPreserving(ai, a),
                       WouldHarmIfDone(ai, a, h),
                   ),
                   Forbidden(ai, a)
               )),
    ]