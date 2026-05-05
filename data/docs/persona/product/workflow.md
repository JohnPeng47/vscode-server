Goal:
To explore Persona's features by creating an identity verification flow for access to generic government services. The workflow is based on an interview with Matthew Cox on Lex Friedman, a former fraudster describing his techniques. In the transcripts, Cox describes many techniques to perform identity fraud. Claude has helpfully put the highlights into a summary here.

I have designed an identity verification pipeline using Persona aimed detecting his techniques.

Detection:
1. Inquiry (itmpl_A1qEZdJuZfvh92dgybU5Ls5RrGP1Ef) ->
    Government ID Verification
    └── verification/government-id
    └── verification/selfie
    └── verification/phone-number

    - Standard Persona identity verification flow, requiring (SSN, address, phone number) along with selfie liveness verification
    - Potential Improvements: adding a government ID requirement to further gate sensitive systems (ie. benefits qualification)

2. Workflow (backend-identity-validation) ->
    > Trigger: inquiry complete
    > Case Creation
        - Start by creating a Case -> this will serve as a single object that will collect the output of the checks below 
    > Parallel Execution
        └── a) Run Address Lookup
        └── b) Run Phone Number Report
        └── c) Run WatchList Report
        └── d) Run Database Verification
                > conditional here that sent (pass_inquiry XOR pass_database_verification) to the Case

    - Blocked by Sandbox:
        - * Photo List: Was going to add the selfie Photo to a List and then use it to match on fraudulent identites that were issued to the same person (Cox used this on 7 DMVs), but this feature was not available on the sandbox plan
            - * Note: the same attack, cross-state DMV applications, would not work as well anymore with AAMVA facilitating cross-state facial recognition checks; that being said, this is America, and participation in this program varies state by state
        - * SSN List: Wanted to do a similar thing with SSNs, storing (SSN, name, DOB, address, phone-number) from the Database Verification and checking if (SSN, name, DOB) was being used to register for a different identity with different (address, phone-number) pairs
            - But couldn't figure out a way to store (SSN, name, DOB, address, phone-number) since Lists only supported single value tuples
            - Potential solution was to use a HTTP Request to store the value outside of Persona, but this was also not enabled in the sandbox

Conclusion:
The most effective detection for Cox's techniques would have been doing facial recognition matching and flagging that the same person (selfie) have registered different identities with different SSNs. Modern fraud actors may have already evolved beyond this, relying on the use of identity mules.
Missing from above is Persona's Graph feature, which is (I think) built specifically to help fraud cases by providing a way to query information surfaced in the identity layer and connect them to events downstream. 

Persona Account: john@bastionone.net
Inquiry: https://app.withpersona.com/dashboard/inquiry-templates/itmpl_A1qEZdJuZfvh92dgybU5Ls5RrGP1Ef/itmplv_A1qEZdJTpbZiQm6y1UDhBe8Kebt9tY/flow
Workflow: https://app.withpersona.com/dashboard/workflows/wfl_A1qEZdJiG2PWghquvzvi2EsYxiPsdD?version=wfv_A1qEZdJt43RFsddd48N3YFL9cAjTac