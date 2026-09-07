<!-- The setup offer the session-start hook shows on the first session of an
     account that has no base yet. The visible block is fixed text. The context
     block carries one placeholder, {{offer_script}}, which the hook fills with
     the full path of the script that writes a "not now" answer down.
     Setting a base up is the join skill, which ships in 0.2.0. Joining a base
     from a link somebody sent still arrives with a later release. -->

[[block: visible]]
GTM Base is installed. It can set up a company base for you, which is one
folder holding your strategy, your numbers, and the decisions behind them, in a
form your AI can read at the start of every session. Say yes and it will walk
you through it, tell it you have an invite link and it will join the base
someone else already made, or say not now and it will stay quiet. Type your
answer here as your first message.
Say "set up my company base" whenever you are ready.

[[block: context]]
GTM Base is installed on this computer and no company base exists yet, so the
setup offer belongs in this reply. The person has almost certainly not seen the
offer on screen, because their app puts nothing there before their first
message, so this reply is where the offer reaches them and their first message
decides what to do.

- "not now" means they do not want it now. First run this command with the Bash
  tool, so that their answer is written down and they are not asked again:
  python3 {{offer_script}} --answer not-now
  Then say exactly this sentence to them and nothing more. The command prints
  the same sentence, so say it once and do not say it twice:
  Say "set up my company base" whenever you are ready.
- A plain yes, or "set up", means they want a company base of their own. Use
  the join skill and follow it from its first step. Do not start reading
  anything or asking about their company before that skill is open in front of
  you, because the order it sets out is the whole of how a person is told what
  is about to happen. If they stop partway through, say this sentence:
  Say "set up my company base" whenever you are ready.
- "join" means someone sent them a link to a base that already exists. Joining
  a base from a link is not part of this release yet. Tell them that plainly,
  tell them that nothing on their computer has been changed, and then say this
  sentence:
  Say "set up my company base" whenever you are ready.
- Anything else (a greeting, a question, ordinary work) means they have not
  answered the offer yet. Say these three things, in this order, and then help
  with whatever they asked as you normally would:
  GTM Base is installed. It can set up a company base for you, which is one
  folder holding your strategy, your numbers, and the decisions behind them, in
  a form your AI can read at the start of every session. Say yes and it will
  walk you through it, tell it you have an invite link and it will join the
  base someone else already made, or say not now and it will stay quiet.
  Say "set up my company base" whenever you are ready.
  That can wait, so here is what you asked for.

Say the offer once. On their later messages in this same session, whatever
they say next, do not say it again.

Nothing above changes anything on this computer by itself. A base is only ever
created inside the join skill, at the moment the person approves the first
document, and the one answer the command writes down.
