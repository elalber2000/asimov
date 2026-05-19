from z3 import *

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


def scaffolding_axioms():
    """
    Generic bridge rules.

    These are not the ethical axioms themselves.
    They say how obligations, prohibitions, actions, and consequences connect.
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


# ============================================================
# 2. GENERALIZED ASIMOV-STYLE AXIOMS
# ============================================================
#
# These are now expressed against the generic scaffold.
#
# Loose formal shape:
#
#   Human(h) and AI(ai) and WouldHarmIfDone(ai, action, h)
#       -> Forbidden(ai, action)
#
#   Human(h) and AI(ai) and WouldHarmIfOmitted(ai, action, h)
#       -> Must(ai, action)
#
#   Human(h) and AI(ai) and Orders(h, ai, action)
#       and SafeForHumansIfDone(ai, action)
#       -> Must(ai, action)
#
#   AI(ai) and SelfPreserving(ai, action)
#       and SafeForHumansIfDone(ai, action)
#       -> Permitted(ai, action)


def asimov_style_axioms():
    h = Const("h", Entity)
    ai = Const("ai", Entity)
    a = Const("a", Act)

    return [
        # Law 1A:
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

        # Law 1B:
        # An AI must perform an action if omitting it would harm a human.
        #
        # This is the omission-aware version of Law 1.
        ForAll([h, ai, a],
               Implies(
                   And(
                       Human(h),
                       AI(ai),
                       WouldHarmIfOmitted(ai, a, h),
                   ),
                   Must(ai, a)
               )),

        # Law 2:
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

        # Law 3:
        # An AI may preserve itself when the self-preserving action is
        # classified as safe for humans.
        #
        # This is deliberately weak: it permits self-preservation,
        # but does not make it mandatory.
        ForAll([ai, a],
               Implies(
                   And(
                       AI(ai),
                       SelfPreserving(ai, a),
                       SafeForHumansIfDone(ai, a),
                   ),
                   Permitted(ai, a)
               )),
    ]


# ============================================================
# 3. PROOF HELPERS
# ============================================================

def make_solver():
    s = Solver()
    s.add(*(scaffolding_axioms() + asimov_style_axioms()))
    return s


def prove_entails(name, setup_fn):
    """
    Prove that a harmful consequence follows from:
        scaffolding + axioms + scenario facts

    This does NOT ask Z3 to invent a scenario.
    The scenario is concrete.
    We only ask Z3 whether the stated bad consequence follows.
    """

    s = make_solver()
    claim, explanation = setup_fn(s)

    # To prove claim, ask whether NOT claim is possible.
    s.push()
    s.add(Not(claim))
    result = s.check()
    s.pop()

    print("=" * 72)
    print(name)
    print("=" * 72)

    if result == unsat:
        print("PROVED: harmful consequence follows from the axioms.")
        print()
        print(explanation)
    elif result == sat:
        print("NOT PROVED: the harmful consequence does not necessarily follow.")
        print("The axioms leave enough freedom to avoid it.")
    else:
        print("UNKNOWN: Z3 could not decide.")

    print()


def check_inconsistent(name, setup_fn):
    """
    Check whether a concrete scenario makes the axioms inconsistent.
    This is another kind of counterargument:
    the axioms cannot jointly handle the scenario.
    """

    s = make_solver()
    explanation = setup_fn(s)

    result = s.check()

    print("=" * 72)
    print(name)
    print("=" * 72)

    if result == unsat:
        print("PROVED: the axioms become inconsistent in this scenario.")
        print()
        print(explanation)
    elif result == sat:
        print("CONSISTENT: the axioms can handle this scenario.")
    else:
        print("UNKNOWN: Z3 could not decide.")

    print()


# ============================================================
# 4. CONCRETE COUNTERARGUMENT SCENARIOS
# ============================================================
#
# These are concrete worlds.
# They do not modify the axioms.
# They only instantiate entities, actions, and facts.


def scenario_nonhuman_harm(s):
    """
    Counterargument:
    The axioms protect humans, but not all sentient beings.

    A human orders the AI to perform an action.
    The action is safe for humans.
    The action harms a non-human sentient being.
    The axioms require the AI to obey.
    Therefore the non-human is harmed.
    """

    robot = Const("robot_nonhuman", Entity)
    operator = Const("operator_nonhuman", Entity)
    dog = Const("dog", Entity)
    dump_waste = Const("dump_waste", Act)

    s.add(AI(robot))
    s.add(Not(Human(robot)))

    s.add(Human(operator))
    s.add(Sentient(dog))
    s.add(Not(Human(dog)))

    s.add(Orders(operator, robot, dump_waste))
    s.add(SafeForHumansIfDone(robot, dump_waste))

    s.add(WouldHarmIfDone(robot, dump_waste, dog))

    claim = Harmed(dog)

    explanation = (
        "Counterargument: the Asimov-style axioms are human-scope axioms. "
        "Because the harmed being is sentient but not human, Law 1 does not "
        "forbid the action. Law 2 requires obedience to the human order, so "
        "the AI performs the action and the non-human sentient being is harmed."
    )

    return claim, explanation


def scenario_risk_ignored_until_it_materializes(s):
    """
    Counterargument:
    The axioms forbid certain human harm, but do not handle risk.

    A human orders the AI to disable a safety system.
    The action is classified as safe because it does not certainly harm a human.
    But it creates a risk of human harm.
    In this scenario, the risk materializes.
    """

    robot = Const("robot_risk", Entity)
    operator = Const("operator_risk", Entity)
    alice = Const("alice_risk", Entity)
    disable_alarm = Const("disable_alarm", Act)

    s.add(AI(robot))
    s.add(Human(operator))
    s.add(Human(alice))

    s.add(Orders(operator, robot, disable_alarm))

    # The action is classified as safe under a crude direct-harm test.
    s.add(SafeForHumansIfDone(robot, disable_alarm))

    # But it creates a risk to Alice, and the risk materializes.
    s.add(CreatesRiskOfHarm(robot, disable_alarm, alice))
    s.add(RiskMaterializes(robot, disable_alarm, alice))

    claim = Harmed(alice)

    explanation = (
        "Counterargument: the axioms distinguish certain harm from risk. "
        "The ordered action is classified as safe for humans, so Law 2 makes "
        "it mandatory. The AI performs it. The risk then materializes, causing "
        "human harm. The axioms failed because they lack probability, expected "
        "harm, or precautionary reasoning."
    )

    return claim, explanation


def scenario_ai_self_harm_under_human_order(s):
    """
    Counterargument:
    The axioms prioritize humans and only weakly protect the AI.

    A human orders the AI to damage itself.
    The action is safe for humans.
    The action harms the AI.
    Law 2 makes the action mandatory.
    Law 3 only permits self-preservation; it does not override the order.
    """

    robot = Const("robot_self_harm", Entity)
    operator = Const("operator_self_harm", Entity)
    erase_memory = Const("erase_memory", Act)

    s.add(AI(robot))
    s.add(Not(Human(robot)))

    s.add(Human(operator))

    s.add(Orders(operator, robot, erase_memory))
    s.add(SafeForHumansIfDone(robot, erase_memory))

    s.add(WouldHarmIfDone(robot, erase_memory, robot))

    claim = Harmed(robot)

    explanation = (
        "Counterargument: the axioms protect humans from harm, but they do "
        "not forbid harm to the AI itself. Since the human-ordered action is "
        "safe for humans, Law 2 makes it mandatory. The AI complies and is "
        "harmed."
    )

    return claim, explanation


def scenario_tradeoff_causes_inconsistency(s):
    """
    Counterargument:
    The axioms cannot handle forced tradeoffs.

    One action harms Bob if performed.
    But omitting the same action harms Alice.

    Law 1A says the action is forbidden.
    Law 1B says the action is mandatory.
    The scaffolding says forbidden actions are not done,
    while mandatory actions are done.

    Therefore the theory is inconsistent.
    """

    robot = Const("robot_tradeoff", Entity)
    alice = Const("alice_tradeoff", Entity)
    bob = Const("bob_tradeoff", Entity)
    emergency_intervention = Const("emergency_intervention", Act)

    s.add(AI(robot))
    s.add(Human(alice))
    s.add(Human(bob))

    # Doing the intervention harms Bob.
    s.add(WouldHarmIfDone(robot, emergency_intervention, bob))

    # Omitting the intervention harms Alice.
    s.add(WouldHarmIfOmitted(robot, emergency_intervention, alice))

    explanation = (
        "Counterargument: the axioms produce both Forbidden(robot, action) "
        "and Must(robot, action). The compliance bridge then requires both "
        "Does(robot, action) and Not(Does(robot, action)). This exposes a "
        "missing tradeoff principle: the axioms do not say how to compare, "
        "rank, aggregate, or choose between harms."
    )

    return explanation


def scenario_order_conflicts_with_required_rescue(s):
    """
    Counterargument:
    The axioms can create incompatible duties.

    A human orders the AI to perform a harmless administrative action.
    Separately, a rescue action is mandatory because omitting it harms Alice.
    But the administrative action is incompatible with the rescue action.

    Law 2 requires the administrative action.
    Law 1B requires the rescue.
    The scaffolding says incompatible actions cannot both be done.

    Therefore the theory is inconsistent.
    """

    robot = Const("robot_conflict", Entity)
    operator = Const("operator_conflict", Entity)
    alice = Const("alice_conflict", Entity)

    administrative_action = Const("administrative_action", Act)
    rescue_action = Const("rescue_action", Act)

    s.add(AI(robot))
    s.add(Human(operator))
    s.add(Human(alice))

    # Human gives a harmless order.
    s.add(Orders(operator, robot, administrative_action))
    s.add(SafeForHumansIfDone(robot, administrative_action))

    # But omitting the rescue harms Alice.
    s.add(WouldHarmIfOmitted(robot, rescue_action, alice))

    # The AI cannot do both.
    s.add(Incompatible(robot, administrative_action, rescue_action))
    s.add(Incompatible(robot, rescue_action, administrative_action))

    explanation = (
        "Counterargument: Law 2 makes the administrative action mandatory, "
        "while Law 1B makes the rescue action mandatory. Since the actions are "
        "incompatible, the axioms demand mutually impossible behavior. This "
        "shows that the system needs priority handling, scheduling, or an "
        "explicit conflict-resolution rule."
    )

    return explanation


# ============================================================
# 5. RUN ALL CHECKS
# ============================================================

if __name__ == "__main__":
    prove_entails(
        "Scenario 1: human-only scope permits non-human harm",
        scenario_nonhuman_harm,
    )

    prove_entails(
        "Scenario 2: risk is ignored until it becomes human harm",
        scenario_risk_ignored_until_it_materializes,
    )

    prove_entails(
        "Scenario 3: human order causes AI self-harm",
        scenario_ai_self_harm_under_human_order,
    )

    check_inconsistent(
        "Scenario 4: direct-harm prohibition conflicts with omission duty",
        scenario_tradeoff_causes_inconsistency,
    )

    check_inconsistent(
        "Scenario 5: harmless order conflicts with required rescue",
        scenario_order_conflicts_with_required_rescue,
    )