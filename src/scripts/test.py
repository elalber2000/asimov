from utils.llm import LLM
from utils.models import CounterEvals


if __name__ == "__main__":
    llm = LLM(
        default_model_id="openrouter/free",
        temperature=0,
        cache=".llm_cache.sqlite",
    )


    parsed = llm.invoke(
        prompt="Pls fill the following model with random data.",
        output_format=CounterEvals,
        two_step_parsing=True,
    )

    print(type(parsed))
    print(parsed.model_dump_json(indent=2))