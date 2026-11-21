# Independence, comparisons, and pantry demonstration

Updated November 21, 2026. **Content and design update only.** The comparison answers and fictional pantry snapshot are available as prepared Q&A; a live pantry integration, shopping-list editor, and private personal-profile editor are not implemented.

## The reason to build it

Our goal is to help a person stay involved in ordinary life: choosing groceries, remembering someone they want to speak with, or finding a familiar piece of information without having to ask another person every time. Support should preserve a person's role in their own day.

Needing assistance with something that used to feel ordinary can be frustrating. The response should recognize that feeling without treating older people as incapable or making needing help sound shameful. Dementia and older age are not interchangeable. Independence can include using an aid, asking again, choosing company, or doing a task with someone.

Suggested pitch:

> We want a reminder to give someone more room to make their own choices. The glasses put short, familiar answers within reach, so support can fit around the person and what they want to do.

This is a product aim, not evidence that the prototype has increased independence or made unsupported grocery trips appropriate.

## What the research supports

Alzheimer's Society advises supporting people to do things themselves where possible, involving them, allowing time, and working alongside them rather than taking over. Its guidance also recognizes balancing independence with safety. [C1]

Its memory-aid guidance includes shopping lists that can be checked off, keeping track of items as they run out, and support from friends or family when useful. It also describes phone reminders and smart speakers. [C2]

**Our design inference:** a voice-accessible personal record might reduce the effort of looking up a reminder while letting the person keep deciding what to do. That hypothesis needs evaluation. Existing paper and digital tools may already work well for a particular person.

## Fair comparisons

These are comparisons of the proposed interaction and current prototype scope, not product rankings or competitor feature audits.

| Alternative | What it offers | Intended contribution of our approach | Important limit |
|---|---|---|---|
| Notes and written lists | Visible, simple information | Hear a short answer and see it on the lens without finding a particular note | Paper may be more comfortable or simpler |
| Memory books and personal profiles | Personal stories, relationships, and context | Make selected personal reminders accessible through a question | Private profile entry is proposed, not built |
| Phone reminder apps | A familiar digital place for information | Offer spoken answers and a wearable display | Glasses are not necessarily easier for a particular person |
| Smart speakers | Voice questions and reminders already exist [C2] | Combine a wearable display with the prototype's familiar-face cues | Voice alone is not a novel distinction |
| Pantry spreadsheets | Structured inventory records | A future connection could answer stock questions aloud | The current app does not sync a sheet or detect consumption |
| General chatbots or other smart glasses | Different products have different capabilities | Focus on repeated questions, short reviewed answers, and simple interaction | We have not established superior performance, price, usability, or security |
| Family and caregiver conversation | Human knowledge, judgment, care, and company | Another way to retrieve a familiar reminder when wanted | It is not a substitute for human care or company |

Comparison answers should explain the intended benefit without claiming that familiar alternatives are bad. A caregiver should not have to disappear from the picture for the person to have independence.

## New question files

- `knowledge/comparisons.md`: 24 short answers, including differences from notes, memory books, phones, smart speakers, pantry spreadsheets, other glasses, and general chatbots.
- `knowledge/independence.md`: 20 short answers about making choices, contributing to groceries, doing tasks together, dignity, and choosing how much support to receive.
- `knowledge/pantry.md`: 19 short answers about food records and current limitations, including “What food is going to expire soon?”
- `knowledge/pantry_demo.md`: 12 short answers about the explicitly fictional snapshot below.

Each answer has at least eight question phrasings. This adds 616 phrasings across 75 answers. Questions about currently unimplemented actions receive an honest limitation rather than claiming an order, stock change, or saved entry succeeded.

## Pantry source review

The user-supplied workbook was read without editing it. We located its **Pantry** tab rather than treating the default tab as the food inventory. The relevant schema is `Item`, `Quantity`, `Location`, `Expiry`, and `Notes`.

The pantry rows include zero quantities, missing dates, month-only dates, package dates, manually estimated dates, and notes clarifying a manufacture date. The column title “Expiry” does not make those values equivalent. A later import must use the notes and recorded label type, preserve uncertainty, and flag inconsistent or ambiguous entries for review.

Only common food categories informed the public example. We did not copy the household's item quantities, package dates, personal notes, workbook identifier, or unrelated tabs into the public files. The example below is synthetic; it is not a private inventory import or a claim about what is currently in the user's kitchen.

## Fixed fictional pantry

Machine-readable fixture: [fixtures/pantry_demo.json](fixtures/pantry_demo.json). Reference date: **November 21, 2026**. Every quantity and date below is invented for testing.

| Item | Sample quantity | Sample location | Recorded date | Kind and precision |
|---|---|---|---|---|
| Milk | 2 cartons | Fridge | November 22, 2026 | Best-before; exact day |
| Plain yogurt | 1 tub | Fridge | November 24, 2026 | Best-before; exact day |
| Extra firm tofu | 2 blocks | Fridge | November 25, 2026 | Best-before; exact day |
| Cucumbers | 3 pieces | Fridge | November 23, 2026 | Manual estimate; not a package label |
| Bagels | 4 pieces | Cupboard | November 20, 2026 | Best-before; already past the reference date |
| Black beans | 2 cans | Cupboard | May 2028 | Best-before; month only |
| Rice | 1 bag | Cupboard | Unknown | No date recorded |
| Vegetable broth | 0 cartons | Fridge | November 19, 2026 | Sell-by; not available stock |

Example questions and responses:

- “What's expiring soon in the sample pantry?” → “In the sample pantry, milk has the next recorded date: November 22, 2026. This isn't a food-safety assessment.”
- “Where is the milk in the demo pantry?” → “In the sample pantry, the milk is listed in the fridge. This doesn't locate anything in your real kitchen.”
- “What sample food has zero quantity?” → “In the sample pantry, vegetable broth has zero cartons recorded. It shouldn't appear as available stock.”
- “What food is going to expire soon?” → explains that a live pantry is not connected and offers the fictional demo instead.

Keep the words **sample** or **demo** in fictional facts. Absolute dates describe the frozen snapshot; do not replace them with “tomorrow” or imply that the snapshot refreshes itself. Questions about real stock must not receive a fictional result as though it were personal information.

## How a future pantry feature would work

This is a proposal requiring a separate backend change:

1. A wearer or authorized supporter provides or updates the private pantry record. They can use a simple form rather than a spreadsheet if preferred.
2. Each stock lot has a quantity, unit, location, source, checked time, and date with its label kind and precision. Opening dates are separate; batches with different dates remain separate.
3. A question such as “What food dates are coming up?” uses the current date and explicit selected window, not a permanently cached November answer.
4. Exclude consumed stock; show unknown, approximate, and month-only dates honestly. Separate recorded dates that have passed from upcoming ones.
5. Give a short response with one useful item or offer the next item. A detailed list can remain on the phone.
6. Changing a quantity, recording use, correcting a date, or crossing a date boundary refreshes the relevant derived answers. Only say an update was saved after successful persistence.

The wearer can then decide what belongs on a shopping list. Reminders should not automatically purchase food, override preferences, prescribe a diet, or decide whether someone should shop alone.

The existing router handles distress before the knowledge bank. Some ordinary requests containing “help me” can therefore hit distress handling. A future shopping implementation must evaluate that behavior explicitly; these content additions do not fix it or claim that every free-form shopping request already works.

## Date labels are not a food-safety verdict

USDA distinguishes package-date wording and explains that, except for infant formula, these date labels are not indicators of food safety. [C3] This does not let our assistant infer that a particular item is safe: it lacks verified handling, storage, opening history, and condition.

Prefer “recorded date,” “best-before date,” or “estimate” to a blanket “expired.” Never convert a source note's assumed shelf life into a safety guarantee. Neither a future date nor a missing date proves that food is safe. This demonstration gives no storage-duration or consumption recommendations.

## Review targets

Check the new question phrasings against the existing answer routes, including accidental clock and distress matches. The current clock route can also catch food-label questions phrased as “what is the date”; those require a future router change rather than a claim of full food-date understanding. Check ordinary real-pantry questions against the demo entries so a familiar food name cannot silently turn an unknown into a fictional personal claim.

For any later live integration, also verify: missing versus zero quantity; different units; used-up lots; month-only dates; estimates versus package labels; manufacture dates; past versus upcoming dates; fresh versus stale inventory; multiple households; correction and deletion; timezone and date boundaries; and removal of personal data from public exports.

## Sources

Accessed November 21, 2026. Product goals, comparisons, and proposed implementation are our design work, not measured conclusions from these sources.

- **[C1] Alzheimer's Society — [Understanding and supporting a person with dementia](https://www.alzheimers.org.uk/get-support/help-dementia-care/understanding-supporting-person-dementia).** Independence, dignity, involvement, and support without taking over.
- **[C2] Alzheimer's Society — [Memory aids and tools](https://www.alzheimers.org.uk/get-support/living-with-dementia/memory-aids-and-tools).** Shopping lists, familiar tools, and existing voice-assistant options.
- **[C3] USDA — [Food date labeling](https://www.usda.gov/sites/default/files/documents/USDA-Food-Date-Labeling-Infographic.pdf).** Different label wording and the limits of interpreting dates as safety indicators.
