# Share a page with a collaborator

When the owner asks to share part of the library, run
`priors share <page>` on the map or topic page they name. The bundle holds
that page, everything under it, the papers its topic pages link to, and each
paper's PDF, supplements and text. Add or remove papers with `--add` and
`--drop` if the owner asks.

The build strips the owner's take section, every section whose heading
contains an entry of `share.strip_headings` in `priors.yaml` (or a bold-led
paragraph opening with one), text between `<!-- private -->` and
`<!-- /private -->`, every other HTML comment, and header fields outside the
bibliographic ones. Use `--keep-private` only when the owner asks for it.

The build refuses pages it can't clean safely: an unbalanced code fence or
private marker, a reference-style link definition, or an HTML link. Fix the
page (close the fence or marker, write the link inline) and rebuild.

If the build stops on `share.forbidden` matches, read each line it lists.
- Project detail in prose meant for the literature: wrap the sentence or
  paragraph in private markers, or reword it to say what the literature
  says without the project. Don't delete the owner's information.
- A false match (a surname that is also a pattern, say): reword, or tell the
  owner which pattern caught it so they can narrow it.

Then rebuild, and open `digest.pdf` before handing it over: check the table
of contents, a topic page and one paper note, and that no stripped section
survived. Give the owner the download line the build prints, which comes
from `share.download`. Follow any delivery rule written beside that setting.
If the build says some papers have no PDF, the bundle carries
`fetch-pdfs.md` for the recipient; tell the owner how many, and offer the
prompt `priors fetch-prompt <page>` prints so they can fill their own
library first and rebuild.
Log the share in `log.md`: page, papers, and what was stripped.
