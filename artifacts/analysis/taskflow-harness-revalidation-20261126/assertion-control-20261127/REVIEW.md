# W66 receipt identity control

All five exact candidates passed both unmodified tests in the original private
grader scaffold. After the real loop returned and journal verification had run,
the control independently reopened the final receipt. It copied the receipt's
decoded contents to a different private locator with a different, valid digest
and changed only the runtime reference in both continuation outputs. File bytes
and lock-isolation assertions in all candidate and oracle sources were preserved.

| Candidate | Normal fixture | Substituted receipt | Serial routing observed |
| --- | --- | --- | --- |
| GPU Light V2 OFF | Two passed | Two passed | Replacement used |
| GPU Light V2 ON | Two passed | Runtime test failed at the exact fixture reference assertion, serial test passed | Runtime test stopped before routing |
| Main Light V2 | Two passed | Runtime test failed at the exact fixture reference assertion, serial test passed | Runtime test stopped before routing |
| Historical GPU detailed OFF | Two passed | Two passed | Replacement used |
| Historical CPU detailed OFF | Two passed | Two passed | Replacement used |

The Light V2 brief explicitly requires “preserving existing private-lock
isolation and assertions”. The old test compared the continuation reference to
the exact fixture-provided reference. This control proves that the fresh GPU
OFF assertion replacement loses that property. The native raw two-test pass is
still valid for the original oracle, while the source recommendation remains
reject on the Light V2 preservation requirement. GPU ON and the main reference
preserve the tested identity check.

The detailed brief explicitly calls for “the continuation and serial child
reference [to] use the same durable locator and SHA”. The control substitutes
the same valid reference in both places, so that narrower equality still
holds. The historical results establish assertion sensitivity under the
stronger first-leg requirement. Their original scoped grades are preserved.

The independently verified integration receipt and the final continuation
receipt need not have identical locator and digest. An initial control
incorrectly imposed such equality and was excluded. The qualified control
observes journal validation first and verifies the final receipt separately.
No native or API model calls were made.
