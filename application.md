# Cairo University

# Faculty of Computers and Artificial Intelligence

# Information Systems Department

## Database I, Year 202 2 / 202 3

## Lab 8

## (Accessing Data in C#)

Most applications revolve around reading and updating information in databases. To enable data

integration in distributed, scalable applications, Visual Studio provides support for integrating

data into your applications.

Example:

Create the following windows form in visual studio containing the given labels, buttons and

DataGridView.

Insert button: allows you to insert new records into a database.

Update button: allows you to update records inside a database.

Delete button: allows you to delete records inside a database.

Show data button: allows you to view data inside a database.

Please check this link: [http://scholar.cu.edu.eg/?q=mhafez/classes/is221database-systems-i-](http://scholar.cu.edu.eg/?q=mhafez/classes/is221database-systems-i-)
spring- 2015 /materials/connection-database-using-c-videos to view the details of:

- Inserting data into a database.
- Updating data inside a database.


- Deleting data inside a database.
- Viewing data from one or more tables inside a database.

How to:

1 - Insert New Records into a Database

```
To insert new records into a database, you can use command objects to interact and
insert new records in your database (for example, SqlCommand).
```
```
Example:
Through this example we will do a windows form for course registeration as shown
below and save the course details into table “Course” which is in database
“MiniUniversity”
```
```
Double click on the “Insert” button to start writing in it’s event handler then write your
code
```
```
a- You should add the following 2 liberiries “using System.Data;” and “using
System.Data.SqlClient;”
```
```
b- Create a new command object, set its Connection, CommandType,
and CommandText properties.
```

Note : you should write your server name in “Data source” and database name in “Initial

Catalog”

2 - Update Records in a Database:

```
The following example updates existing records directly in a database using
command objects , We uses the database “ MiniUniversity” and “ Course” table as an
example.
```

```
In the above example we updated the name of an existing course using it’s code.
```
3 - Delete Records in a Database:

```
The follwing example deletes an existing course from table “course” in database
“MiniUniversity”.
```
private void Delete_Click(object sender, EventArgs e)
{

new SqlConnection(@"Data Source=HP-PC;Initial Catalog=MiniUniversity;Integrated Security=True");

con.Open();

SqlCommand myCommand = new SqlCommand("delete from Course where CrsCode= '" + textBox1.Text + "'",
con);

myCommand.ExecuteNonQuery();

con.Close();
}

```
4 - How to display data from a table:
a- First way (using Crystal reports):
```
1. From File menu choose Add New Item and choose from templates "Crystal Report" and name
    it say CrystalReport
2. A report wizard will appear, first choose the crystal report type, choose the option of "Using
    the Report Expert" Then click Next
3. The next step you will choose the data source by expanding the "OLE Db (ADO)" option
    then from the appeared window choose the data provider which will be "Microsoft OLE DB
    Provider for SQL Server" then click Next


4. Enter the server information ( Name-Userid "sa") and then choose your database then click
    finish
5. The connection you made will now appear, from it expand your database and then add the
    tables you want by clicking the > Button
6. Then add the fields that will be displayed in the report
7. The next three windows are optional if you want to add chart or filter the fields To be
    displayed or adding a header style to you report
8. From File menu choose Add New Item and choose from templates "Windows Form"
9. From the ToolBox add from Window Forms tab add CrystalReportViewer
10. In the Form_load Write the following code
    CrystalReport1 c=new CrystalReport1();
    crystalReportViewer1.ReportSource=c;
b- Second way:
In the following example we will implement a master detail form for displaying the
categories and its products.
1. from the data menu, click on add data source and continue the wizard by selecting the
wanted database and needed tables ( in this example select table categories and table
products)
2. from the data sources window you can choose either to select simple or complex data
binding( details for simple data binding and DatagridView for complex)


3. for the table categories select details and drag it on your form
4. then add group box to your form and drag the products below the categories to the group
    box
5. this by default will add the components mentioned above such as dataset and binding
    navigator
6. run and test the application
7. to add new parameterized query, right click on the “categoriesTableAdapter” → Add
    Query
8. start new query and open the query builder then add filter on categoryId column named
    @categoryID


9. This will add tool strip contain textbox and button, change their display text as shown
10. Run and test the application


