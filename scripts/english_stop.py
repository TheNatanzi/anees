"""Common English words that must never be matched to a Doc word when they appear as Latin tokens in a transcript
(the lessons are ~60-90% English). Extend freely; a miss here shows up as a false 'Doc word said' event."""
ENGLISH_STOP = set("""
a an and the this that these those there here it its it's is are was were be been being am i'm i've i'll i'd you you're you've
you'll your yours he she they them their theirs we we're we've we'll our ours us me my mine him her his who whom whose which what
when where why how not no yes yeah yep nope ok okay oh ah um uh hmm mm so but or if then than as of at by for from in into on onto
to too up down out over under with without about above below between through during before after again also always never
sometimes often just only very really quite rather almost already still yet ever even much many more most less least few some
any all both each every either neither none one two three four five six seven eight nine ten first second third next last other
another same different new old good bad big small long short high low right wrong true false same such own can can't could
couldn't should shouldn't would wouldn't will won't shall may might must do does did done don't doesn't didn't have has had having
haven't hasn't hadn't make makes made making get gets got getting give gives gave given go goes went going gone come comes came
coming take takes took taking put puts say says said saying tell tells told telling ask asks asked know knows knew known think
thinks thought see sees saw seen look looks looked want wants wanted need needs needed use uses used using try tries tried
work works worked call calls called mean means meant feel feels felt let lets keep keeps kept start started stop stopped
like likes liked love happy sad tired bored scared angry ready funny nice great fine well better best worse worst
because cause 'cause since while until though although unless whether so that in order once twice maybe perhaps probably
actually basically literally exactly kind sort thing things something anything nothing everything someone anyone everyone
nobody people person man woman boy girl child friend teacher student word words sentence verb noun adjective plural singular
past present future tense form forms example examples question answer lesson class today tomorrow yesterday now later
morning evening night week weekend month year time times day days hour minute second
add added remove removed change changed learn learned study studied practice practiced remember forget forgot understand
understood repeat repeated write wrote read speak spoke talk talked listen heard hear finish finished end ended
al ma am an ben bin been being fill has had ai has us use tell all mad made past boat sin em ma we gosh they're we're you're i'm it's that's there's what's he's she's let's qeem
""".split())
