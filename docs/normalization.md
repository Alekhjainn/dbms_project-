# Database Normalization Process

## Unnormalized Form (UNF)
In a flat file, a single "Library Record" might look like:
`Member_ID, Member_Name, Member_Email, Member_Type, Max_Books, Loan_Days, Fine_Per_Day, Issue_Date, Due_Date, Return_Date, Fine_Amount, Copy_Accession_No, Copy_Status, Edition_ISBN, Book_Title, Author_Names, Category_Names, Publisher_Name`

This format suffers from heavy data redundancy (updating a member's name requires updating every issue record they have) and anomalies.

## First Normal Form (1NF)
**Rule**: Ensure every column is atomic (indivisible) and there are no repeating groups.
- `Author_Names` and `Category_Names` are separated into intersection tables.
- Each issue is a separate row.

## Second Normal Form (2NF)
**Rule**: Must be in 1NF. Every non-key attribute must be fully functionally dependent on the entire primary key (no partial dependencies).
- Removing partial dependencies by breaking down entities:
- `Member` entity: `Member_ID -> Name, Email, Member_Type`
- `Issue` entity: `Issue_ID -> Copy_ID, Member_ID, Issue_Date...`
- `Book` entity: `Book_ID -> Title`
- `Edition` entity: `Edition_ID -> Book_ID, Publisher_ID, ISBN`

## Third Normal Form (3NF)
**Rule**: Must be in 2NF. Every non-key attribute must be non-transitively dependent on the primary key (no transitive dependencies).
- Transitive dependency found: `Member_ID -> Member_Type -> Max_Books, Loan_Days, Fine_Per_Day`.
- **Resolution**: Create a `Loan_Policy` table. 
  - `Loan_Policy (Member_Type PK, Max_Books, Loan_Days, Fine_Per_Day)`
  - `Member` now only holds `Member_Type` as a Foreign Key.

## Boyce-Codd Normal Form (BCNF)
**Rule**: Every determinant must be a candidate key.
Our schema satisfies BCNF. `ISBN` determines `Edition_ID`, but `ISBN` is a candidate key. `Accession_No` determines `Copy_ID`, and it is a candidate key.

All tables in `schema_sqlite.sql` and `schema_postgres.sql` strictly adhere to 3NF/BCNF.
