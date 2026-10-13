# Egoola Seller Guide

**One guide for everyone.** This guide explains, in simple words, how sellers work on Egoola:
how a seller joins, how we check them, how they log in, and what they and the admins can do.

It is written for all teams: operations, support, product, design, testing and development.
You do not need any technical knowledge to read it.

This guide does **not** explain technical details such as API addresses or the database. Each team
has its own document for that.

---

## 1. The people in this guide

| Who | What they do |
|---|---|
| **Seller** | A person or business that wants to sell on Egoola. |
| **Admin** | A member of the Egoola team who works in the admin panel. Admins check new sellers and manage them. |
| **Operations / support team** | Helps sellers and admins. They use the admin panel too. |

---

## 2. The most important idea: two separate settings

Every seller has **two settings**. They are different things. Please do not mix them up.

### Setting 1: the verification result ("Is this seller approved?")

This is the result of checking the seller's documents. It has four values:

| Value | What it means |
|---|---|
| **Unverified** | The seller just joined. Nobody has looked yet. |
| **Pending** | An admin is checking, or the seller sent their application again after a rejection. |
| **Verified** | The seller is **approved**. Their documents are good. |
| **Rejected** | The admin said no. The seller must fix something. A reason is always given. |

**"Approved" means "Verified". Nothing else.**

### Setting 2: the account switch ("Can this seller work right now?")

This is like an on/off switch for the account. It has three values:

| Value | What it means |
|---|---|
| **Active** | The account is switched on. |
| **Inactive** | The account is switched off **for the time being**. The seller can still log in, but can only change their own profile. They can do nothing else until an admin switches them to Active. |
| **Suspended** | The seller is **blocked**. They cannot log in at all. |

A new seller starts as **Inactive**. An admin can also make an approved seller **Inactive** (for example, to
pause them) and make them **Active** again later.

### Putting the two together

A seller can use **all** seller features only when they are **Verified and Active**. We say they
**can operate**. Every other seller can only manage their own profile.

| Seller situation | Verification | Account switch | Can log in? | Can edit own profile? | Can use full seller features? |
|---|---|---|---|---|---|
| Just joined | Unverified | Inactive | Yes | Yes | **No** |
| Application sent again, waiting | Pending | Inactive | Yes | Yes | **No** |
| Rejected | Rejected | Inactive | Yes | Yes (to fix and send again) | **No** |
| Approved and working | Verified | Active | Yes | Yes | **Yes** |
| Approved but paused by an admin | Verified | Inactive | Yes | Yes | **No** (until an admin makes them Active) |
| Blocked | Any | Suspended | **No** | No | No |

Remember: **Inactive does not mean "not approved".** A seller can be approved and still be Inactive.

---

## 3. Registration flow

There are two ways a seller can be created.

### 3.1 The seller joins by themselves (the normal way)

**What the seller does**

1. Opens the sign-up page and fills in the form.
2. Chooses their place from lists: country, then state, then city, then (if they want) thana. Each list
   depends on the one before it.
3. Uploads their identity documents.
4. Sends the form.

**What the seller must give**

| Item | Rule |
|---|---|
| Name | Required. |
| Email | Required. Must not be used by another seller. Big or small letters do not matter. It is not used to log in. |
| Phone number | Required. Must not be used by another seller. **This is what the seller uses to log in.** |
| Password | Required. At least 8 characters. Not a very common password (like "password123"). Not only numbers. |
| Present address | Required. Where they live now. |
| Permanent address | Required. |
| Country, state, city | Required. The state must be inside the country, and the city inside the state. |
| Thana | Optional. If given, it must be inside the city. |
| **National ID (NID)** | **Required. At least one file.** Many sellers upload a front and a back picture. |
| Profile photo | Optional. |
| Other documents | Optional: birth certificate, certificate, or "other". |
| Business profile | Optional. See below. |

**About the documents**

- Allowed file types: JPG, PNG, WEBP or PDF.
- Each file can be up to 5 MB.
- Up to 10 files can be sent at one time.

**About the optional business profile**

A seller can describe their business now or later. If they fill it in, these six things are needed:
type of business, main product, owner name, number of employees (a range), yearly income (a range),
and the year the business started. These are optional: a description, a public email, WhatsApp,
Facebook, WeChat, Skype, and the business place.

**What happens after the seller sends the form**

- If something is wrong (for example the email is already used), the form shows what to fix. **Nothing
  is saved** until everything is correct.
- If everything is correct, the seller is created with:
  - Verification: **Unverified**
  - Account switch: **Inactive**
  - A mark that says "this seller is waiting for an admin". This puts them in the admin's **Seller Request** list.
- The seller sees a "thank you, we will review your documents" message.
- **The seller can log in right away** to complete their profile. They cannot sell yet.

> **Important for support:** a seller who was rejected **cannot sign up again** with the same phone number
> or email, because those are already taken. They should **log in and send their application again**
> (see section 4.4). Do not create a second account for them.

### 3.2 An admin creates the seller

An admin can add a seller directly from the admin panel (for example, a seller we already know and trust).

- The admin fills in the same details. A password is needed.
- By default this seller is **Verified** and **Active**, so they can work at once. The admin can choose
  different settings when creating.
- This seller does **not** appear in the Seller Request list, because nobody needs to review them.

### 3.3 What admins see: the Seller Request list

The **Seller Request** list shows the sellers who are **waiting for an admin to act**.

- It shows sellers who joined by themselves, and sellers who sent their application again after a rejection.
- The **newest request is at the top**. Admins can also sort with the oldest request first (first come, first served).
- It is a list that grows while admins work, so it loads in small groups ("Load more"). It does not show a
  total count. A separate number on the menu shows how many are waiting.
- Admins can search and filter by: name, email or phone; verification result; account switch; place
  (country, state, city, thana); whether a business profile was given; the type of business; the date
  they joined; and the date they asked for review.

**When does a seller leave the Seller Request list?**

A seller leaves the list the first time an admin **really changes** their **verification result** or
**account switch** (for example Approve, Reject, Mark as pending, Pause, or Suspend).

These things do **not** remove a seller from the list:

- An admin only fixes the seller's name, address, documents or business profile.
- An admin only writes a note without changing the status.
- A rejection that was not completed (for example, the reason was missing).

A seller comes back to the list only if they join, or **send their application again** after a rejection.

---

## 4. Verification flow

Verification means: "An admin checks the seller's documents and decides."

### 4.1 Admin steps

1. Open the **Seller Request** list and pick a seller (usually the one at the top).
2. Open the seller's page. The admin can see:
   - the personal details and both addresses,
   - the uploaded documents (pictures open on the page, PDFs open in a new tab),
   - the business profile (if any),
   - the **review history** (every decision so far), and
   - the **profile change history** (every change to the profile, with before and after).
3. Decide:

| Decision | What the admin does | What happens |
|---|---|---|
| **Approve** | Sets Verification to **Verified** and the account switch to **Active** (both, in one go). | The seller can now operate. They leave the Seller Request list. |
| **Reject** | Sets Verification to **Rejected** and **writes a reason**. | The seller stays Inactive. They can fix and send again. They leave the Seller Request list. The reason is required. |
| **Mark as pending** | Sets Verification to **Pending**. | Means "I am checking this". The seller leaves the Seller Request list. |

> **Approve needs both settings.** Verified alone is not enough for a seller to work: the account switch
> must also be Active. This is on purpose, so an admin can approve a seller but keep the account off.

**About the reason (note)**

- A rejection **must** have a reason. Without it, the rejection is not saved and nothing changes.
- The reason belongs to the **current** result only. When the result changes again, the old reason is not
  carried over. (It stays in the review history, so nothing is lost.)
- Write the reason so the seller understands what to fix, for example: "The NID picture is blurry. Please upload a clear picture."

**The review history**

Every time the verification result really changes, one line is added to the history: who did it
(seller or admin and their name), when, the new result, and the reason if any. The first line is
always the sign-up itself. Lines are never edited or removed.

### 4.2 What the seller sees

| Seller's result | What the seller should see after logging in |
|---|---|
| Unverified or Pending | "Your application is under review." They can edit their profile. |
| Rejected | The **reason**, and a **Send again** button. They can fix their profile and documents. |
| Verified and Inactive | "Your account is paused. An admin has to make it active again." |
| Verified and Active | The normal seller area. |

### 4.3 When a seller is approved

- The seller can use all seller features (as they are built; see section 9).
- **Identity documents are locked.** The seller can no longer add or remove their NID or birth
  certificate by themselves. If one must change, they ask an admin, and an admin changes it.
  This protects the check we already did. The seller can still change everything else: their name,
  address, photo, business profile, and other documents like certificates.
- The seller **cannot approve themselves**. Verification and the account switch can only be changed by an admin.

### 4.4 When a seller is rejected: fix and send again

1. The seller logs in (a rejected seller **can** log in) and reads the reason.
2. They fix their profile and documents. For example, they remove the blurry NID and upload a clear one.
3. They press **Send again**. They can write a short message to the admin if they like.
4. What happens:
   - The result becomes **Pending**.
   - The seller goes back into the admin's **Seller Request** list, at the **top**, as a new request.
   - A new line is added to the review history, made by the seller, with their message.
   - The old rejection reason stays in the history.
   - The account switch stays **Inactive** until an admin approves.
5. The admin reviews again and approves or rejects.

Only a **rejected** seller can send the application again. Others cannot.

### 4.5 The whole verification flow in one picture

```
Seller joins  ->  Unverified + Inactive  ->  appears in "Seller Request" list
                                |
                        Admin checks documents
              ______________|______________________________
             |                             |                |
          APPROVE                       REJECT         MARK PENDING
   Verified + Active               Rejected + reason     ("I am checking")
             |                             |
   Seller can operate           Seller logs in, reads reason,
   (ID documents locked)        fixes things, presses "Send again"
                                           |
                                Pending, back at the TOP of the list
                                           |
                                    Admin checks again
```

---

## 5. Login flow

### 5.1 How a seller logs in

1. The seller enters their **phone number** and **password** on the login page. (**Sellers log in with their phone number, not their email.** Admins and buyers still use their email.)
2. If both are correct and the seller is not suspended, they get in.
3. The app then looks at the seller's two settings and shows the right screens (see section 4.2).

```
Phone number + password
          |
   Wrong, or not registered? -----> "Invalid phone number or password."
          |
   Suspended? ---------------------> "This account is not active."
          |
   Otherwise: logged in
          |
   Verified AND Active?  --yes-->  normal seller area
          |
          no
          v
   Profile screens only, with a message:
   under review / rejected + reason + "Send again" / paused
```

### 5.2 Who can log in

| Seller | Can log in? | What they can do after logging in |
|---|---|---|
| Unverified, Pending, or Rejected (Inactive) | **Yes** | Edit their own profile only. |
| Verified and Inactive (paused) | **Yes** | Edit their own profile only. |
| Verified and Active | **Yes** | Everything a seller can do. |
| **Suspended** | **No** | Nothing. They see: "This account is not active." |

If the phone number or password is wrong, the seller sees: "Invalid phone number or password." We do not say which one
is wrong, to keep accounts safe. The same message is shown if the phone number is not registered.

The seller must type the phone number the same way they gave it at sign-up (for example, with the same country code).
Spaces before or after the number do not matter.

### 5.3 Staying logged in

- After login, the seller stays signed in for a while. The app renews the session by itself.
- If the seller has not used Egoola for about two weeks, they must log in again.

### 5.4 When an admin changes something while the seller is logged in

The seller's settings are checked **every time** they do something. So changes work **at once**:

- If an admin **suspends** the seller, the seller is signed out on their very next action, and cannot log in again. They see: "This account is not active."
- If an admin **pauses** (Inactive) an approved seller, they can still use their profile but nothing else.
- If an admin **approves** or **activates** a seller, they can start operating without logging in again, once the app refreshes their state.

### 5.5 Forgotten password

A "forgot password" flow is **not built yet** (see section 9). Until then, support should ask an admin to
set a new password for the seller.

### 5.6 Who else logs in

Admins and buyers have their own login pages. A seller's login does **not** open the admin panel. If a seller
tries an admin page, it is refused.

---

## 6. Seller actions flow

This section lists what each person can do after the seller exists.

### 6.1 What a seller can do (their own profile)

These actions are open to every seller who is **not suspended**, whatever their verification result.

| Action | Details |
|---|---|
| **See their profile** | Details, place, business profile, documents, the verification result, and the rejection reason (if any). |
| **Change name** | Allowed. |
| **Change profile photo** | Allowed. The old photo is deleted from storage. |
| **Change addresses and place** | Allowed. Present and permanent addresses cannot be empty. Country, state and city cannot be empty. The place choices must match each other. |
| **Change skills, education, experience, interests** | Allowed. |
| **Add or change the business profile** | Allowed. If they send it, the six required business items must all be there. |
| **Add a document** | Allowed. JPG, PNG, WEBP or PDF, up to 5 MB each, up to 10 at once. |
| **Delete a document** | Allowed, with the rules below. The file is deleted from storage. |
| **Replace a document** | Delete the old one and upload the new one in the same step. |
| **Change password** | Allowed. They must type the current password. The new password must follow the password rules and be different from the old one. |
| **Send application again** | Only when Rejected (section 4.4). |

**Rules for documents**

- **Before the seller is Verified** (just joined, pending, or rejected), they can change **any** document, including the
  NID. This is how a rejected seller fixes their application.
- There must **always be at least one NID**. A seller cannot delete their only NID. To change it, they
  upload the new NID and remove the old one in the same step.
- After the seller is **Verified**, the **NID and birth certificate are locked**. The seller cannot add,
  delete or replace them. An admin can. Certificates and "other" documents can still be changed.
- A seller can only touch their **own** documents.

**What a seller can NOT do**

- Change their **email** or **phone number** (not available for now). The phone number is their login, so this is protected. If a seller needs this, they ask support, and an admin changes it. Then tell the seller their new login number.
- Change their own verification result or account switch. Only admins can.
- See the profile change history. Only admins can.
- Use the full seller features while they are not Verified and Active.

### 6.2 What an admin can do with sellers

| Action | Details |
|---|---|
| **See all sellers** | A list with search and filters (same filters as the Seller Request list). Shows the seller's results, switch, and dates. |
| **Open a seller** | See everything: details, documents, business profile, review history, profile change history. |
| **Add a seller** | Section 3.2. |
| **Edit a seller** | Change any detail, including **email, phone and password** (the phone number is the seller's login, so if it changes, the seller must log in with the new number), and add or remove documents. Admins are not stopped by the "locked after verification" rule. |
| **Approve / Reject / Mark pending** | Section 4.1. |
| **Pause a seller** (Inactive) | The seller stays approved, can still log in and edit the profile, but cannot work. This does **not** put them back in the Seller Request list. |
| **Make a seller Active again** | The seller can work again (if they are Verified). |
| **Suspend a seller** | The seller is blocked at once. They cannot log in. |
| **Delete a seller** | The seller, their history and **all their uploaded files** are removed for good. This cannot be undone. |

**Suspend or Pause?**

- Use **Pause (Inactive)** when you want the seller to stop working for a while but still be able to log in and fix their profile.
- Use **Suspend** when the seller must be blocked completely.

### 6.3 The profile change history (admins only)

Every time a seller's profile is saved and something **really changed**, the system writes **one record**.
This is done for changes by the seller **and** by an admin.

What a record shows:

- **Who** made the change (seller or admin, and their name) and **when**.
- **What** changed.
- The **old value** and the **new value** for each thing that changed.

Example: in one save, a seller changed their name and address. That is **one** record that shows the old name
and old address next to the new name and new address.

What is tracked: name, email, phone, both addresses, place, profile photo, skills/education/experience/interests,
the business profile, and the documents (which were added or removed).

A password change is recorded as "password changed". **The password itself is never saved or shown.**

Changes to the verification result or account switch are **not** in this history. They are in the **review history** (section 4.1).

If a save changes nothing, nothing is recorded. Records are never edited or deleted.

### 6.4 What happens to files

- When a document is deleted, its file is **deleted from storage** straight away.
- When a profile photo is replaced, the old photo file is deleted.
- When an admin deletes a seller, all of that seller's files (documents and photo) are deleted.
- If a change is refused (for example, "you cannot delete your only NID"), **no file is deleted**.

---

## 7. Quick rules (one page)

| Topic | Rule |
|---|---|
| Joining | NID is required. Email and phone must be new. |
| Password | At least 8 characters. Not common. Not only numbers. |
| Files | JPG, PNG, WEBP or PDF. 5 MB each. Up to 10 at a time. |
| New seller | Unverified + Inactive + waiting in the Seller Request list. |
| Admin-created seller | Verified + Active by default. Not in the Seller Request list. |
| Approve | Needs **Verified + Active** together. |
| Reject | Needs a reason. |
| Seller Request list | Newest request first. A seller leaves it when an admin really changes their verification result or account switch. |
| Rejected seller | Can log in, fix, and send again. Cannot sign up again with the same phone or email. |
| Send again | Only for Rejected. Becomes Pending. Goes to the top of the list. |
| Inactive | Can log in, profile only. Used for new sellers and for paused sellers. |
| Suspended | Cannot log in. |
| Can operate | Only **Verified + Active**. |
| Login | A seller logs in with **phone number + password** (not email). |
| Email and phone | The seller cannot change them (for now). Admins can. If the phone changes, the seller's login changes with it. |
| ID documents | Locked for the seller once Verified. Admins can change them. |
| Always one NID | A seller cannot delete their only NID. |
| History | Review history (decisions) and profile change history (edits) are seen by admins only. |
| Deleting | Deletes the files from storage too. |

---

## 8. Questions we often get (for support and operations)

**A seller says: "I signed up but I cannot sell."**
Normal. They must be **Verified and Active**. Check the Seller Request list and review their documents.

**A seller says: "I was rejected. I try to sign up again but it says my phone/email is already used."**
Correct. Ask them to **log in**, read the reason, fix their documents, and press **Send again**. Do not create a new account.

**A seller cannot see a "Send again" button.**
The button is only for sellers whose result is **Rejected**. If they are Pending, they are already waiting for review.

**A seller wants to change their phone number or email.**
They cannot do it themselves (for now). An admin edits the seller. The change is recorded in the profile change history. If it is the phone number, tell the seller: it is their login now, and the old number will not work.

**A seller wants to change their NID after being approved.**
They cannot. An admin changes it. Tip: ask the seller to send the new document through support, check it, and then replace it on their profile.

**A seller says: "My account says it is paused."**
An admin made it Inactive. Find out why. When it is fine, an admin makes the seller **Active** again.

**A seller says: "I cannot log in with my email."**
Sellers log in with their **phone number**, not their email. Ask them to use the phone number they gave at sign-up.

**A seller says: "I cannot log in."**
- Wrong phone number or password? Ask them to try again with the exact phone number they gave at sign-up, or an admin sets a new password. Remember: a seller does **not** log in with their email.
- Message "This account is not active"? The seller is **Suspended**. Only an admin can change that.

**How do I stop a seller for a short time but let them fix their profile?**
Make them **Inactive** (pause). Make them **Active** again later.

**How do I block a seller completely?**
**Suspend** them.

**Did the seller get an email when I approved or rejected them?**
**No.** There are no automatic messages yet. Please tell the seller yourself (see section 9).

**Who can see what the seller changed?**
Only admins, on the seller's page, in the profile change history.

**I deleted a seller by mistake.**
Deleting is permanent: the seller and their files are gone. The seller must sign up again. Please be careful and, when unsure, use **Suspend** or **Pause** instead.

---

## 9. Not available yet

Please do not promise these to sellers yet.

- **Messages to sellers** (email, SMS or app notification) when they are approved, rejected, or paused. For now, support must tell them.
- **Email and phone code checks** (confirming that the email and phone really belong to the seller).
- **Seller changing their own email or phone.**
- **"Forgot password"** by the seller. For now, an admin sets a new password.
- **Checking each document separately** (for example, accept the NID but ask for a new certificate). Today the decision is for the whole seller.
- **Some seller features** are still being built: orders, the wallet and withdrawals. **Products and gigs are ready** (see the Egoola Listing Guide, which has a Gigs section): only sellers who are **Verified and Active** can use them. A seller who cannot operate sees a clear message that says whether they are "not approved yet" or "inactive".
- **A limit on how often someone can send the sign-up form** (to stop misuse). This will be added before launch.

---

## 10. Words used in this guide

| Word | Meaning |
|---|---|
| **Application** | A seller's sign-up and documents that wait for a check. |
| **Approved** | The same as **Verified**. |
| **Verified** | An admin checked the documents and said yes. |
| **Pending** | Waiting for, or being checked by, an admin. |
| **Rejected** | An admin said no and gave a reason. |
| **Active / Inactive / Suspended** | The account switch (section 2). |
| **Can operate** | Verified **and** Active. |
| **Seller Request list** | The admin's list of sellers who are waiting for an admin to act. |
| **Send again** | A rejected seller sends their fixed application for a new check. |
| **NID** | National ID. Required for every seller. |
| **Review history** | The list of every verification decision for a seller. |
| **Profile change history** | The list of every change to a seller's profile, with old and new values. |
