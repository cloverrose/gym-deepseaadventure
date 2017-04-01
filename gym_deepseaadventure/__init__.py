from gym.envs.registration import register

register(
    id='deepseaadventure-v0',
    entry_point='gym_deepseaadventure.envs:DeepSeaAdventureEnv',
)
