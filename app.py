import streamlit as st  # pip install streamlit
import pandas as pd  # pip install pandas
import plotly.express as px  # pip install plotly-express
import base64  # Standard Python Module
from io import StringIO, BytesIO  # Standard Python Module
import Pressure_functions as PF
import os


def generate_excel_download_link(df):
    # Credit Excel: https://discuss.streamlit.io/t/how-to-add-a-download-excel-csv-function-to-a-button/4474/5
    towrite = BytesIO()
    df.to_excel(towrite, encoding="utf-8", index=False, header=True)  # write to BytesIO buffer
    towrite.seek(0)  # reset pointer
    b64 = base64.b64encode(towrite.read()).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="data_download.xlsx">Download Excel File</a>'
    return st.markdown(href, unsafe_allow_html=True)

def generate_html_download_link(fig):
    # Credit Plotly: https://discuss.streamlit.io/t/download-plotly-plot-as-html/4426/2
    towrite = StringIO()
    fig.write_html(towrite, include_plotlyjs="cdn")
    towrite = BytesIO(towrite.getvalue().encode())
    b64 = base64.b64encode(towrite.read()).decode()
    href = f'<a href="data:text/html;charset=utf-8;base64, {b64}" download="plot.html">Download Plot</a>'
    return st.markdown(href, unsafe_allow_html=True)


st.set_page_config(page_title='Dive Bug')
st.title('Dive Bug 📈')
st.subheader('Feed me with a hex file:')

uploaded_file = st.file_uploader('Choose a text file with the hex values', type='txt')


st.markdown('---')
if uploaded_file:
    stringio = StringIO(uploaded_file.getvalue().decode("utf-8")).getvalue()
    # st.write(stringio)
    file_path = uploaded_file.name
    print(stringio)
    with open(file_path, 'w') as file:
        file.write(str(stringio))
    # df = pd.read_excel(uploaded_file, engine='openpyxl')

File_chosen = st.selectbox(
    'Which File would you like to analyse?',
    PF.list_text_files(),
)
print(f"Processing {File_chosen}")
new_name = st.text_input("Change File Name", "NA.txt")
if not new_name.lower().endswith('.txt'):
    new_name += '.txt'
if st.button("Change File Name",type="primary"):
    with open(File_chosen, 'r') as file:
        content = file.read()
    with open(new_name, 'w') as file:
        file.write(content)
        if os.path.exists(File_chosen):
            # Delete the file
            os.remove(File_chosen)
    st.rerun()

else:
    st.write("No New name")

processed_data = PF.get_processed_data(File_chosen)
fig1,fig2 = PF.produce_plots(processed_data)

# # -- GROUP DATAFRAME
# output_columns = ['Sales', 'Profit']
# df_grouped = df.groupby(by=[groupby_column], as_index=False)[output_columns].sum()

# # -- PLOT DATAFRAME
# fig = px.bar(
#     df_grouped,
#     x=groupby_column,
#     y='Sales',
#     color='Profit',
#     color_continuous_scale=['red', 'yellow', 'green'],
#     template='plotly_white',
#     title=f'<b>Sales & Profit by {groupby_column}</b>'
# )
st.plotly_chart(fig1)


# -- DOWNLOAD SECTION
st.subheader('Download:')
# generate_excel_download_link(df_grouped)
generate_html_download_link(fig1)
st.markdown('---')
st.plotly_chart(fig2)
generate_html_download_link(fig2)
