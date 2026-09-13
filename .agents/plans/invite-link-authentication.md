# Invite-link authentication

## 1. Desired outcome and user-visible behavior

Replace the public user chooser with closed, invite-link authentication while
preserving every valid live session during deployment.

Signed-out users can:

- create a new account only through a valid new-person invite;
- sign into an existing account through that account's self-invite; and
- recover an existing account with its recovery code.

Signed-in users can generate, on demand:

- a new-person invite valid for seven days;
- a self-invite valid for 24 hours and bound to their account; and
- an initial or replacement recovery code.

New accounts receive a recovery code immediately after creation. Successful
recovery invalidates the submitted code and displays a replacement once.

## 2. Scope and non-goals

### In scope

- Invite generation and consumption screens.
- New-account creation with unique display names.
- Self-invite confirmation and device transfer.
- Public recovery-code authentication.
- Recovery-code generation and replacement in Settings.
- Sliding 30-day server-side session expiry.
- Backward-compatible session migration that preserves live authentication.
- Friendly states for invalid credentials and invalid form submissions.
- Necessary Cork and Helios session-framework changes.
- Removal of the public user chooser.

### Non-goals

- Passwords, email addresses, or external identity providers.
- Selecting an existing account from a new-person invite.
- Outstanding-invite lists or invite revocation.
- Limiting a user to one outstanding invite of either type.
- User-facing session lists or a "sign out all devices" action.
- Account deletion or user administration.
- Automated recovery after both the session and recovery code are lost.
- Administrative recovery screens or commands.
- Repairing the repository's disposable development users.
- General CSRF or rate-limiting work.
- Changing Cork's current production `Secure` cookie configuration.

## 3. Confirmed decisions and assumptions

- One Invite model represents both invite types. An optional target user
  distinguishes a self-invite from a new-person invite.
- New-person invites only create accounts.
- Self-invites can authenticate only the user who generated them.
- Invite tokens are generated only after a signed-in user explicitly requests one.
- Multiple unconsumed invites of either type may remain valid simultaneously.
- Only hashed invite tokens are persisted. The usable token is shown only in the
  generated link.
- New-person invites expire after seven days.
- Self-invites expire after 24 hours.
- Settings exposes separate new-person and self-invite actions, with no
  outstanding-invite list or revoke interface.
- Self-invites use a confirmation screen and are consumed only by its submission.
- Invite consumption is rejected while already signed in and does not switch
  accounts or consume the invite.
- Display names are stored with surrounding whitespace removed and compared
  case-insensitively for uniqueness.
- Live data contains no duplicate display names. Repository-local data may be
  invalidated as needed.
- Recovery codes are 10-character, case-insensitive, unambiguous alphanumeric
  values.
- Existing users do not receive an interrupting recovery-code screen. They may
  generate a code from Settings.
- Creating a replacement recovery code invalidates the previous code.
- Recovery-code acknowledgment is lightweight and unenforced: the one-time display
  offers an "I've saved it—continue" action without storing acknowledgment state.
- Existing session IDs are preserved during migration. Legacy sessions with a
  still-present browser cookie are treated as active and gain activity metadata on
  their next request.
- Administrative recovery remains future work.

## 4. User/workflow scenarios and acceptance criteria

### Existing signed-in user after deployment

- Their current cookie continues authenticating the same user.
- Their first request does not rotate or replace the session ID.
- The request initializes missing server-side activity metadata and renews the
  30-day expiry.
- They are not forced through invitation, recovery, or onboarding.
- Their existing boards, pins, sharing, and preferences are unchanged.

### Generate a new-person invite

- A signed-in user requests an invite from Settings.
- Cork creates the invite at that moment and displays a copyable link.
- The link remains valid for seven days and can be used once.
- Generating it does not sign out or otherwise affect the creator.

### Create an account from an invite

- A signed-out recipient opens a valid new-person invite and sees a display-name
  form.
- They cannot select or authenticate as an existing user.
- Surrounding whitespace is removed from the submitted name.
- Empty or case-insensitively duplicate names produce a useful validation message
  without consuming the invite.
- Successful submission creates the user, consumes the invite, and creates a
  session.
- A recovery code is generated and displayed once before the user continues to
  Cork.
- Reusing the link or submitting it concurrently cannot create another account.

### Generate and consume a self-invite

- A signed-in user requests a self-invite from Settings.
- Cork displays a link valid for 24 hours and bound to that exact user.
- Opening it while signed out shows a confirmation naming the account.
- Confirming consumes the invite and creates a session for that account.
- It does not replace or reveal the account's recovery code.
- The invite cannot be modified to select another user.
- Opening or submitting an expired or previously consumed link does not
  authenticate anyone.
- Opening it while signed in does not consume it or switch identities.

### Recover an account

- The signed-out screen no longer enumerates users and instead explains that an
  invite or recovery code is required.
- Entering a valid recovery code creates a session for its associated user.
- The submitted code is immediately invalidated.
- A replacement code is generated and displayed once.
- Invalid codes do not identify whether any particular account exists.
- Replaying the old code fails.

### Manage recovery while signed in

- An existing user without a code can generate one from Settings.
- A user with a code can deliberately replace it.
- Only the newly generated plaintext code is displayed; persisted state contains
  its protected representation.
- Navigating away means the displayed code cannot be retrieved again.

### Invalid invite links

- Malformed, unknown, expired, and already-consumed invite links share one generic
  user-facing error state.
- These failures do not expose invite metadata or account identity.
- Failed consumption does not create a user or authenticated session.

### Session expiry and sign-out

- Each authenticated request renews both the browser cookie and server-side
  activity deadline to 30 days.
- A session inactive for more than 30 days is rejected even if its cookie is
  submitted manually.
- Expired server-side records can be removed without affecting active sessions.
- Signing out invalidates only the current session and returns to the new signed-out
  screen.
- Existing cookie-policy behavior is preserved.

## 5. Delivery steps

1. **Establish session compatibility**
   - Add server-side activity and expiry behavior without changing the identity or
     ID of active legacy sessions.
   - Handle legacy records that lack activity metadata.
   - Add safe removal of expired and administratively invalidated sessions.
   - Preserve current cookie-policy configuration.

2. **Add authentication data and credential handling**
   - Add an optional protected recovery credential to users so existing records
     remain readable.
   - Add the single Invite model with creator, creation, expiry, consumption, and
     optional target-user information.
   - Generate high-entropy invite tokens and persist only their hashes.
   - Ensure only one-time link and recovery values are shown to users; never persist
     their plaintext values in application data.

3. **Replace signed-out authentication**
   - Remove the user chooser and direct user-ID sign-in.
   - Add recovery-code submission and generic failure handling.
   - Update sign-out language that currently refers to returning to the chooser.

4. **Implement invite generation**
   - Add separate Settings actions for new-person and self-invites.
   - Generate each link only in response to its action.
   - Present the resulting link clearly without adding invite-management screens.

5. **Implement invite consumption**
   - Route both invite types through a shared entry workflow backed by the single
     Invite model.
   - Present account creation for new-person invites and confirmation for
     self-invites.
   - Revalidate expiry and single-use state at submission time.
   - Make successful consumption and its associated account/session change behave
     as one operation so retries or concurrent submissions cannot reuse an invite.
   - Reject signed-in consumption before making any changes.

6. **Implement recovery-code presentation and replacement**
   - Show a newly created account's initial code once before continuing.
   - Allow signed-in users to generate or replace their code from Settings.
   - On successful signed-out recovery, invalidate the submitted code, authenticate
     the user, and display its replacement once.
   - Keep acknowledgment presentational rather than introducing an onboarding
     state or additional guard.

7. **Prepare and perform the deployment**
   - Verify the live user names satisfy the new uniqueness rule before rollout.
   - Snapshot both application records and session records before deployment.
   - Deploy without clearing or rewriting valid session IDs.
   - Confirm legacy sessions acquire activity metadata lazily as their users return.

## 6. Validation approach

- Add end-to-end request tests covering invite generation, account creation,
  self-invite confirmation, recovery, cookie handling, and sign-out.
- Start from a legacy session document with no activity metadata and prove that the
  existing cookie remains authenticated with the same ID after its first upgraded
  request.
- Verify active sessions slide to 30 days while sessions beyond the inactivity
  window are rejected and removable.
- Verify both invite expirations at their boundaries using controlled time.
- Verify multiple invites for the same creator can remain valid and be consumed
  independently.
- Verify a token is single-use under retries and competing submissions.
- Verify persisted data contains invite hashes and recovery hashes, but no usable
  invite tokens or plaintext recovery codes.
- Verify display-name trimming, case-insensitive uniqueness, empty-name rejection,
  and non-consumption after validation errors.
- Verify a new-person invite cannot authenticate an existing identity.
- Verify a self-invite cannot authenticate any user other than its target.
- Verify signed-in invite visits neither switch accounts nor consume tokens.
- Verify malformed, unknown, expired, and consumed links render the same generic
  failure state.
- Verify recovery rotates the code and rejects replay of the old code.
- Verify existing users can continue without a recovery code and can later create
  one from Settings.
- Run the complete Cork and Helios test suites and lint checks.
- In deployment smoke testing, confirm an existing browser remains signed in, then
  exercise one new-person invite, one device transfer, and one recovery cycle.

## 7. Open questions or decisions still needing review

None.
