import pandas as pd
from collections import Counter
from sqlalchemy import create_engine, select, text

from mna_due_diligence.db import Contract, FileState
from mna_due_diligence.index.config import get_config


config = get_config()
db_url = config.DB_URL
# Replace async drivers with sync equivalents
if '+asyncpg' in db_url:
    db_url = db_url.replace('+asyncpg', '')  # postgresql+asyncpg -> postgresql
elif '+aiosqlite' in db_url:
    db_url = db_url.replace('+aiosqlite', '')  # sqlite+aiosqlite -> sqlite
elif '+aiomysql' in db_url:
    db_url = db_url.replace('+aiomysql', '+pymysql')  # mysql+aiomysql -> mysql+pymysql
elif '+asyncmy' in db_url:
    db_url = db_url.replace('+asyncmy', '+pymysql')  # mysql+asyncmy -> mysql+pymysql
    
    
db_engine = create_engine(db_url, echo=False, future=True)


# retrieve the whole contracts metadata as a dataframe
with db_engine.connect() as connection:
    result = connection.execute(text("SELECT * FROM contract_metadata"))
    metadata_df = pd.DataFrame(result.fetchall(), columns=result.keys())
    
# process the metadata_df to get the aligned filenames
metadata_df['normed_filename'] = metadata_df['filename'].apply(lambda x: x.split('\\')[-1])



def create_gt_data(clause_type: str, 
                   master_clause_csv_file: str,
                   number_of_top_parties: int = 5):
    
    df = pd.read_csv(master_clause_csv_file)
    df_sl = df[df[f"{clause_type}-Answer"]== 'Yes']
    print(f"[GT-DATA] Obtained {len(df_sl)} files having clause type {clause_type}")
    
    # find the top parties involved in these contracts
    df_sl_filenames = df_sl['Filename'].tolist()
    meta_df_sl = metadata_df[metadata_df['normed_filename'].isin(df_sl_filenames)]
    party_a_list = meta_df_sl['party_a'].tolist()
    party_b_list = meta_df_sl['party_b'].tolist()
    parties_counter = Counter(party_a_list + party_b_list)
    top_parties = [party for party, count in parties_counter.most_common(number_of_top_parties)]
    print(f"[GT-DATA] Top {number_of_top_parties} parties involved: {top_parties}")
    
    # filenames for each top party
    party_wise_filenames = {}
    for party in top_parties:
        party_df = meta_df_sl[(meta_df_sl['party_a'] == party) | (meta_df_sl['party_b'] == party)]
        party_wise_filenames[party] = party_df['normed_filename'].tolist()
        print(f"[GT-DATA] Party: {party} -> {len(party_wise_filenames[party])} files")
        
    # fetch the clause text for these files
    party_wise_data = {}
    for party, filenames in party_wise_filenames.items():
        clause_texts = []
        for filename in filenames:
            clause_row = df_sl[df_sl['Filename'] == filename]
            if not clause_row.empty:
                clause_text = clause_row.iloc[0][f"{clause_type}"]
                clause_texts.append({
                    "filename": filename,
                    "clause_text": clause_text
                })
        party_wise_data[party] = clause_texts
    
    return party_wise_data