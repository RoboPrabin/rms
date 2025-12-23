import pandas as pd
import streamlit.components.v1 as components
import math
from time import sleep
from config import config
import streamlit as st
from utils import helper
import streamlit_bridge.app_state as app_state
import streamlit_bridge.navigation as navigation
import os
import uuid
from datetime import datetime
from sqlalchemy import create_engine, text
from db import db
from PIL import Image
import os
from utils.custom_hotkey import activate_client_code_hotkey


class Gallery:
    THUMB_SIZE = (300, 300)  # Thumbnail size
    PHOTOS_PER_PAGE = 20

    @staticmethod
    @st.cache_data
    def get_thumbnail(path):
        """Generate thumbnail if not exists and cache it."""
        thumb_dir = os.path.join(os.path.dirname(path), "thumbs")
        os.makedirs(thumb_dir, exist_ok=True)
        thumb_path = os.path.join(thumb_dir, os.path.basename(path))
        if not os.path.exists(thumb_path):
            img = Image.open(path)
            img.thumbnail(Gallery.THUMB_SIZE)
            img.save(thumb_path)
        return thumb_path
    

    def __init__(self):
        st.set_page_config("Gallery", page_icon="📸", layout='wide')

        activate_client_code_hotkey()

        # Authentication
        app_state.restore_state_from_query_params()
        app_state.sync_query_params_from_session()
        app_state.check_authenticaiton_state()

        self.username, self.role = app_state.get_current_user_info()

        # Sidebar
        navigation.render_sidebar()
        st.header("📸 Trishakti Gallery", anchor=False)

    def render_upload_section(self):
        conn = db.get_connection()
        cur = conn.cursor()

        # ---------- CATEGORY ----------
        cur.execute("SELECT id, name FROM photo_category ORDER BY name")
        categories = cur.fetchall()
        category_map = {name: cid for cid, name in categories}
        col1, col2, col3 = st.columns(3)
        with col1:
            selected_category = st.selectbox(
                "Select Category",
                ["-- Select --"] + list(category_map.keys())
            )

        if selected_category == "-- Select --":
            st.info("Select a category to continue")
            return

        category_id = category_map[selected_category]

        # ---------- ALBUM ----------
        cur.execute(
            """
            SELECT id, title
            FROM photo_album
            WHERE category_id = %s
            ORDER BY created_at DESC
            """,
            (category_id,)
        )
        albums = cur.fetchall()
        album_map = {title: aid for aid, title in albums}

        with col2:
            selected_album = st.selectbox(
                "Select Album",
                ["-- Select --"] + list(album_map.keys())
            )
        with col3:
            # ---------- ADD ALBUM ----------
            st.markdown("<br>", unsafe_allow_html=True)  # 👈 alignment spacer
            with st.expander(f"➕ Add new album for category: {selected_category}"):
                album_title = st.text_input("Album title *").title()
                album_desc = st.text_area("Description (Optional)")

                if st.button("Create album"):
                    if not album_title.strip():
                        st.warning("Album title required")
                        return

                    try:
                        cur.execute(
                            """
                            INSERT INTO photo_album
                            (category_id, title, description, created_by)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (
                                category_id,
                                album_title.strip().title(),
                                album_desc.strip(),
                                self.username
                            )
                        )
                        conn.commit()
                        st.success("Album created")
                        st.rerun()
                    except Exception:
                        st.error("Album already exists in this category")

        if selected_album == "-- Select --":
            st.info("Select or create an album to upload photos")
            return

        album_id = album_map[selected_album]

        # ---------- FILE UPLOADER ----------
        if "uploader_key" not in st.session_state:
            st.session_state.uploader_key = 0

        uploaded_files = st.file_uploader(
            "Upload photos",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key=f"photo_uploader_{st.session_state.uploader_key}"
        )

        if st.button("🚀 Upload"):
            if not uploaded_files:
                st.warning("Please select at least one file")
                return

            user_dir = os.path.join(
                config.GALLERY_PATH,
                selected_category,
                selected_album,
                self.username
            )
            os.makedirs(user_dir, exist_ok=True)

            for file in uploaded_files:
                ext = os.path.splitext(file.name)[1]
                stored_name = f"{uuid.uuid4()}{ext}"
                full_path = os.path.join(user_dir, stored_name)

                with open(full_path, "wb") as f:
                    f.write(file.getbuffer())

                cur.execute(
                    """
                    INSERT INTO photo (
                        original_filename,
                        stored_filename,
                        file_path,
                        category_id,
                        album_id,
                        uploaded_by,
                        file_size,
                        mime_type
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        file.name,
                        stored_name,
                        full_path,
                        category_id,
                        album_id,
                        self.username,
                        file.size,
                        file.type
                    )
                )

            conn.commit()
            st.success("Photos uploaded successfully ✅")
            st.session_state.uploader_key += 1
            st.rerun()



    # def render_gallery_section(self):
    #     conn = db.get_connection()
    #     cur = conn.cursor()

    #     # --- Filters ---
    #     cur.execute("SELECT id, name FROM photo_category ORDER BY name")
    #     categories = cur.fetchall()
    #     category_map = {name: cid for cid, name in categories}
    #     col1, col2, col3 = st.columns(3)
    #     with col1:
    #         selected_category = st.selectbox("Filter by Category", ["All"] + list(category_map.keys()))

    #     album_map = {}
    #     selected_album = "All"
    #     if selected_category != "All":
    #         cur.execute(
    #             "SELECT id, title FROM photo_album WHERE category_id=%s ORDER BY created_at",
    #             (category_map[selected_category],)
    #         )
    #         albums = cur.fetchall()
    #         album_map = {title: aid for aid, title in albums}
    #         with col2:
    #             selected_album = st.selectbox("Filter by Album", ["All"] + list(album_map.keys()))

    #     my_only = st.checkbox("Show only my uploads")

    #     # --- Build query ---
    #     query = """
    #         SELECT p.original_filename, p.file_path, p.uploaded_by, a.title, c.name
    #         FROM photo p
    #         LEFT JOIN photo_album a ON a.id = p.album_id
    #         LEFT JOIN photo_category c ON c.id = p.category_id
    #         WHERE 1=1
    #     """
    #     params = []

    #     if selected_category != "All":
    #         query += " AND c.id = %s"
    #         params.append(category_map[selected_category])

    #     if selected_album != "All":
    #         query += " AND a.id = %s"
    #         params.append(album_map[selected_album])

    #     if my_only:
    #         query += " AND p.uploaded_by = %s"
    #         params.append(self.username)

    #     query += " ORDER BY p.uploaded_at DESC"
    #     cur.execute(query, params)
    #     rows = cur.fetchall()
    #     if not rows:
    #         st.info("No photos found")
    #         return

    #     # --- Pagination ---
    #     total_photos = len(rows)
    #     total_pages = math.ceil(total_photos / self.PHOTOS_PER_PAGE)
    #     with col3:
    #         page = st.number_input("Page", min_value=1, max_value=total_pages, value=1)
    #     start = (page - 1) * self.PHOTOS_PER_PAGE
    #     end = start + self.PHOTOS_PER_PAGE
    #     rows_page = rows[start:end]

    #     # --- Dialog function using decorator ---
    #     @st.dialog(".", width='medium')
    #     def show_full_image(fname, path, category, album, user):
    #         st.image(path, use_column_width=True, width='content')
    #         st.markdown(f"**Category:** {category}  \n**Album:** {album}  \n**Uploaded by:** {user}")

    #     # --- Display thumbnails ---
    #     cols_per_row = 4
    #     num_rows = math.ceil(len(rows_page) / cols_per_row)

    #     for row_idx in range(num_rows):
    #         cols = st.columns(cols_per_row)
    #         for col_idx in range(cols_per_row):
    #             idx = row_idx * cols_per_row + col_idx
    #             if idx >= len(rows_page):
    #                 break
    #             fname, path, user, album, category = rows_page[idx]
    #             thumb_path = self.get_thumbnail(path)

    #             with cols[col_idx]:
    #                 st.image(thumb_path, use_column_width=True, caption=category, clamp=True)
    #                 # st.caption(f"\n{category} → {album}\n\nBy: {user}")
    #                 st.markdown(
    #                         f"""
    #                         <p style="margin:0">{category}: <b>{album}</b></p>
    #                         <p style="margin:0 0 5px 0; color:gray">By: {user}</p>
    #                         """,
    #                         unsafe_allow_html=True
    #                     )

    #                 # Open dialog on button click
    #                 if st.button("View Full Image", key=f"view_{idx}"):
    #                     show_full_image(fname, path, category, album, user)
    #         st.markdown("---")


    # def render_gallery_section(self):
    #     conn = db.get_connection()
    #     cur = conn.cursor()

    #     # --- Fetch categories ---
    #     cur.execute("SELECT id, name FROM photo_category ORDER BY name")
    #     categories = cur.fetchall()
    #     category_map = {name: cid for cid, name in categories}

    #     # --- Fetch distinct uploaders ---
    #     cur.execute("SELECT DISTINCT uploaded_by FROM photo ORDER BY uploaded_by")
    #     uploaders = [row[0] for row in cur.fetchall()]

    #     # --- Filters UI ---
    #     col1, col2, col3 = st.columns([2, 2, 2])
    #     with col1:
    #         selected_category = st.selectbox("Filter by Category", ["All"] + list(category_map.keys()))
    #     with col2:
    #         selected_uploader = st.selectbox("Filter by Uploaded By", ["All"] + uploaders)
    #     with col3:
    #         sort_option = st.selectbox("Sort By", ["Latest", "Oldest"])

    #     my_only = st.checkbox("Show only my uploads")

    #     # --- Fetch albums for selected category ---
    #     album_map = {}
    #     selected_album = "All"
    #     if selected_category != "All":
    #         cur.execute(
    #             "SELECT id, title FROM photo_album WHERE category_id=%s ORDER BY created_at",
    #             (category_map[selected_category],)
    #         )
    #         albums = cur.fetchall()
    #         album_map = {title: aid for aid, title in albums}
    #         selected_album = st.selectbox("Filter by Album", ["All"] + list(album_map.keys()))

    #     # --- Build query ---
    #     query = """
    #         SELECT p.original_filename, p.file_path, p.uploaded_by, a.title, c.name, p.uploaded_at
    #         FROM photo p
    #         LEFT JOIN photo_album a ON a.id = p.album_id
    #         LEFT JOIN photo_category c ON c.id = p.category_id
    #         WHERE 1=1
    #     """
    #     params = []

    #     if selected_category != "All":
    #         query += " AND c.id = %s"
    #         params.append(category_map[selected_category])

    #     if selected_album != "All":
    #         query += " AND a.id = %s"
    #         params.append(album_map[selected_album])

    #     if selected_uploader != "All":
    #         query += " AND p.uploaded_by = %s"
    #         params.append(selected_uploader)

    #     if my_only:
    #         query += " AND p.uploaded_by = %s"
    #         params.append(self.username)

    #     # --- Sorting ---
    #     query += " ORDER BY p.uploaded_at DESC" if sort_option == "Latest" else " ORDER BY p.uploaded_at ASC"

    #     cur.execute(query, params)
    #     rows = cur.fetchall()
    #     if not rows:
    #         st.info("No photos found")
    #         return

    #     # --- Pagination ---
    #     total_photos = len(rows)
    #     total_pages = math.ceil(total_photos / self.PHOTOS_PER_PAGE)
    #     page = st.number_input("Page", min_value=1, max_value=total_pages, value=1)
    #     start = (page - 1) * self.PHOTOS_PER_PAGE
    #     end = start + self.PHOTOS_PER_PAGE
    #     rows_page = rows[start:end]

    #     # --- Dialog function ---
    #     @st.dialog(".", width='medium')
    #     def show_full_image(fname, path, category, album, user):
    #         st.image(path, use_column_width=True)
    #         st.markdown(f"**Category:** {category}  \n**Album:** {album}  \n**Uploaded by:** {user}")

    #     # --- Display thumbnails ---
    #     cols_per_row = 4
    #     num_rows = math.ceil(len(rows_page) / cols_per_row)
    #     for row_idx in range(num_rows):
    #         cols = st.columns(cols_per_row)
    #         for col_idx in range(cols_per_row):
    #             idx = row_idx * cols_per_row + col_idx
    #             if idx >= len(rows_page):
    #                 break
    #             fname, path, user, album, category, _ = rows_page[idx]
    #             thumb_path = self.get_thumbnail(path)

    #             with cols[col_idx]:
    #                 st.image(thumb_path, use_column_width=True)
    #                 st.markdown(
    #                     f"""
    #                     <p style="margin:0">{category}: <b>{album}</b></p>
    #                     <p style="margin:0 0 5px 0; color:gray">By: {user}</p>
    #                     """,
    #                     unsafe_allow_html=True
    #                 )
    #                 if st.button("View Full Image", key=f"view_{idx}"):
    #                     show_full_image(fname, path, category, album, user)

    #         st.markdown("---")



    def render_gallery_section(self):
        conn = db.get_connection()
        cur = conn.cursor()

        # --- Fetch categories ---
        cur.execute("SELECT id, name FROM photo_category ORDER BY name")
        categories = cur.fetchall()

        category_map = {name: cid for cid, name in categories}

        # --- Fetch distinct uploaders ---
        cur.execute("SELECT DISTINCT uploaded_by FROM photo ORDER BY uploaded_by")
        uploaders = [row[0] for row in cur.fetchall()]
   
        # --- Filters UI ---
        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            selected_category = st.selectbox("Filter by Category", ["All"] + list(category_map.keys()))
        with col2:
            selected_uploader = st.selectbox("Filter by Uploaded By", ["All"] + uploaders)
        with col3:
            sort_option = st.selectbox("Sort By", ["Latest", "Oldest"])


        # st.badge(f"Total image: {total_images} ", color='green')
        # --- Fetch albums for selected category ---
        album_map = {}
        selected_album = "All"
        if selected_category != "All":
            cur.execute(
                "SELECT id, title FROM photo_album WHERE category_id=%s ORDER BY created_at",
                (category_map[selected_category],)
            )
            albums = cur.fetchall()
            album_map = {title: aid for aid, title in albums}
            selected_album = st.selectbox("Filter by Album", ["All"] + list(album_map.keys()), width=360)

        st.markdown("<br>", unsafe_allow_html=True)  # 👈 alignment spacer
        my_only = st.checkbox("Show only my uploads")
        st.markdown("---")
        st.markdown("<br>", unsafe_allow_html=True)  # 👈 alignment spacer
        # --- Build query ---
        query = """
            SELECT p.id, p.original_filename, p.file_path, p.uploaded_by, a.title, c.name, p.uploaded_at
            FROM photo p
            LEFT JOIN photo_album a ON a.id = p.album_id
            LEFT JOIN photo_category c ON c.id = p.category_id
            WHERE 1=1
        """
        params = []

        if selected_category != "All":
            query += " AND c.id = %s"
            params.append(category_map[selected_category])

        if selected_album != "All":
            query += " AND a.id = %s"
            params.append(album_map[selected_album])

        if selected_uploader != "All":
            query += " AND p.uploaded_by = %s"
            params.append(selected_uploader)

        if my_only:
            query += " AND p.uploaded_by = %s"
            params.append(self.username)

        # --- Sorting ---
        query += " ORDER BY p.uploaded_at DESC" if sort_option == "Latest" else " ORDER BY p.uploaded_at ASC"

        cur.execute(query, params)
        rows = cur.fetchall()
        if not rows:
            st.info("No photos found")
            return

        # --- Pagination setup ---
        if "gallery_page" not in st.session_state:
            st.session_state.gallery_page = 1

        total_photos = len(rows)
        total_pages = math.ceil(total_photos / self.PHOTOS_PER_PAGE)
        page = st.session_state.gallery_page
        start = (page - 1) * self.PHOTOS_PER_PAGE
        end = start + self.PHOTOS_PER_PAGE
        rows_page = rows[start:end]

        # --- Dialog for full image ---
        @st.dialog("Full Image", width='medium')
        def show_full_image(fname, path, category, album, user):
            st.image(path, use_column_width=True)
            st.markdown(f"**Category:** {category}  \n**Album:** {album}  \n**Uploaded by:** {user}")

        # --- Display thumbnails ---
        cols_per_row = 4
        num_rows = math.ceil(len(rows_page) / cols_per_row)
        for row_idx in range(num_rows):
            cols = st.columns(cols_per_row)
            for col_idx in range(cols_per_row):
                idx = row_idx * cols_per_row + col_idx
                if idx >= len(rows_page):
                    break
                pid, fname, path, user, album, category, _ = rows_page[idx]
                thumb_path = self.get_thumbnail(path)  # Assuming you have this function

                with cols[col_idx]:
                    st.image(thumb_path, use_column_width=True)
                    st.markdown(
                        f"""
                        <p style="margin:0">{category}: <b>{album}</b></p>
                        <p style="margin:0 0 5px 0; color:gray">By: {user}</p>
                        """,
                        unsafe_allow_html=True
                    )
                    if st.button("View Full Image", key=f"view_{pid}"):
                        show_full_image(fname, path, category, album, user)

            st.markdown("---")
        # st.markdown("---")

        # --- Centered pagination buttons ---
        with st.container():
            cols = st.columns([2,1.3,1.2,1,3])  # 7 columns to leave space on sides
            # Put buttons in the middle 4 columns
            with cols[1]:
                if st.button("⏮️ First Page") and page != 1:
                    st.session_state.gallery_page = 1
                    st.rerun()
            with cols[2]:
                if st.button("◀️ Previous") and page > 1:
                    st.session_state.gallery_page = page - 1
                    st.rerun()
            with cols[3]:
                if st.button("Next ▶️") and page < total_pages:
                    st.session_state.gallery_page = page + 1
                    st.rerun()
            with cols[4]:
                if st.button("⏭️ Last Page") and page != total_pages:
                    st.session_state.gallery_page = total_pages
                    st.rerun()


        # Optional: show page info
        st.markdown(f"Page {page} of {total_pages} ({total_photos} photos)")



    def add_category(self):
        mode = st.radio("Select option", ['Add', 'Rename'], horizontal=True)
        conn = db.get_connection()
        cur = conn.cursor()
        if mode == 'Add':
            # --- Add new category ---
            with st.form("add_category", clear_on_submit=True):
                new_category = st.text_input("Category name")

                if st.form_submit_button("Create category", icon="➕"):
                    if new_category.strip():
                        try:

                            cur.execute(
                                """
                                INSERT INTO photo_category (name,created_by)
                                VALUES (%s, %s)
                                """,
                                (new_category.strip().title() ,self.username)
                            )
                            conn.commit()
                            st.success("Category added.")
                            sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Category '{new_category}' already exists or invalid.", icon="🚨")
                    else:
                        st.warning("Category name required")
        else:
            # --- Rename existing category ---
            cur.execute("SELECT id, name FROM photo_category ORDER BY name")
            categories = cur.fetchall()
            if not categories:
                st.info("No categories found to rename")
                return

            category_map = {name: cid for cid, name in categories}
            with st.form("rename_category", clear_on_submit=True):
                selected_category = st.selectbox("Select Category to Rename", list(category_map.keys()))
                new_name = st.text_input("New Category Name")

                if st.form_submit_button("Rename Category", icon="✍🏼"):
                    if not new_name.strip():
                        st.warning("Please enter a new name")
                        return

                    try:
                        cur.execute(
                            """
                            UPDATE photo_category
                            SET name = %s
                            WHERE id = %s
                            """,
                            (new_name.strip().title(), category_map[selected_category])
                        )
                        conn.commit()
                        st.success(f"Category '{selected_category}' renamed to '{new_name.strip().title()}' ✅")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to rename category: {e}")

    def rename_album(self):
        conn = db.get_connection()
        cur = conn.cursor()

        # --- Select category ---
        cur.execute("SELECT id, name FROM photo_category ORDER BY name")
        categories = cur.fetchall()
        category_map = {name: cid for cid, name in categories}

        selected_category = st.selectbox(
            "Select Category",
            ["-- Select --"] + list(category_map.keys())
        )
        if selected_category == "-- Select --":
            st.info("Select a category to continue")
            return

        category_id = category_map[selected_category]

        # --- Select album created by current user ---
        cur.execute(
            "SELECT id, title FROM photo_album WHERE category_id=%s AND created_by=%s ORDER BY created_at",
            (category_id, self.username)
        )
        albums = cur.fetchall()
        if not albums:
            st.info("No albums created by you in this category")
            return

        album_map = {title: aid for aid, title in albums}
        selected_album = st.selectbox("Select Album to rename", list(album_map.keys()))
        new_name = st.text_input("New Album Name").strip().title()

        if st.button("Rename Album"):
            if not new_name:
                st.warning("Please enter a new name")
                return
            try:
                cur.execute(
                    """
                    UPDATE photo_album
                    SET title = %s
                    WHERE id = %s AND created_by = %s
                    """,
                    (new_name, album_map[selected_album], self.username)
                )
                conn.commit()
                st.success(f"Album '{selected_album}' renamed to '{new_name}' ✅")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to rename album: {e}")


    def transfer_photo(self):
        conn = db.get_connection()
        cur = conn.cursor()

        # --- Source Category & Album ---
        cur.execute("SELECT id, name FROM photo_category ORDER BY name")
        categories = cur.fetchall()
        category_map = {name: cid for cid, name in categories}

        src_category = st.selectbox("Source Category", ["-- Select --"] + list(category_map.keys()))
        if src_category == "-- Select --":
            st.stop()
        src_category_id = category_map[src_category]

        cur.execute(
            "SELECT id, title FROM photo_album WHERE category_id=%s ORDER BY created_at",
            (src_category_id,)
        )
        albums = cur.fetchall()
        album_map = {title: aid for aid, title in albums}

        if not album_map:
            st.info("No albums found in this category")
            st.stop()

        src_album = st.selectbox("Source Album", list(album_map.keys()))
        src_album_id = album_map[src_album]

        # --- Fetch photos uploaded by current user ---
        cur.execute("""
            SELECT id, original_filename, file_path
            FROM photo
            WHERE album_id=%s AND uploaded_by=%s
            ORDER BY uploaded_at
        """, (src_album_id, self.username))
        photos = cur.fetchall()
        if not photos:
            st.info("No photos uploaded by you in this album")
            st.stop()

        st.markdown("**Select photos to transfer:**")
        selected_photo_ids = []

        # Display photos in grid with checkbox
        cols = st.columns(4)
        for idx, (pid, fname, fpath) in enumerate(photos):
            col = cols[idx % 4]
            with col:
                st.image(fpath, use_container_width=True)
                if st.checkbox("Select", key=f"photo_{pid}"):
                    selected_photo_ids.append(str(pid))  # Ensure UUID is string
                st.caption(fname)

        # --- Destination Category & Album ---
        dest_category = st.selectbox("Destination Category", ["-- Select --"] + list(category_map.keys()), key="dest_cat")
        if dest_category == "-- Select --":
            st.stop()
        dest_category_id = category_map[dest_category]

        cur.execute("SELECT id, title FROM photo_album WHERE category_id=%s ORDER BY created_at", (dest_category_id,))
        dest_albums = cur.fetchall()
        dest_album_map = {title: aid for aid, title in dest_albums}

        if not dest_album_map:
            st.info("No albums in destination category")
            st.stop()

        dest_album = st.selectbox("Destination Album", list(dest_album_map.keys()), key="dest_album")
        dest_album_id = dest_album_map[dest_album]

        # --- Transfer Action ---
        if st.button("Transfer Selected Photos"):
            if not selected_photo_ids:
                st.warning("Select at least one photo to transfer")
                st.stop()

            try:
                # Correct UUID array casting for PostgreSQL
                cur.execute(
                    """
                    UPDATE photo
                    SET album_id = %s, category_id = %s
                    WHERE id = ANY(%s::uuid[])
                    """,
                    (dest_album_id, dest_category_id, selected_photo_ids)
                )
                conn.commit()
                st.success(f"Transferred {len(selected_photo_ids)} photo(s) to album '{dest_album}' ✅")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to transfer photos: {e}")



    def render_my_photos_section(self):
        """Show only images uploaded by current user with delete option."""
        conn = db.get_connection()
        cur = conn.cursor()

        # Fetch photos uploaded by this user
        cur.execute("""
            SELECT p.id, p.original_filename, p.file_path, a.title, c.name
            FROM photo p
            LEFT JOIN photo_album a ON a.id = p.album_id
            LEFT JOIN photo_category c ON c.id = p.category_id
            WHERE p.uploaded_by = %s
            ORDER BY p.uploaded_at DESC
        """, (self.username,))
        rows = cur.fetchall()

        if not rows:
            st.info("You have not uploaded any photos yet.")
            return

        # --- Display thumbnails with delete ---
        cols_per_row = 4
        num_rows = math.ceil(len(rows) / cols_per_row)

        for row_idx in range(num_rows):
            cols = st.columns(cols_per_row)
            for col_idx in range(cols_per_row):
                idx = row_idx * cols_per_row + col_idx
                if idx >= len(rows):
                    break
                photo_id, fname, path, album, category = rows[idx]
                thumb_path = self.get_thumbnail(path)

                with cols[col_idx]:
                    st.image(thumb_path, use_column_width=True)
                    # st.caption(f"{fname}\n{category} → {album}")
                    st.markdown(
                            f"""
                            <p style="margin:0 0 5px 0">{category}: <b>{album}</b></p>
                            """,
                            unsafe_allow_html=True
                        )

                    # Delete button
                    if st.button("🗑 Delete", key=f"delete_{photo_id}"):
                        try:
                            # Delete file from filesystem
                            if os.path.exists(path):
                                os.remove(path)

                            # Delete row from DB
                            cur.execute("DELETE FROM photo WHERE id = %s", (photo_id,))
                            conn.commit()

                            st.success(f"Deleted {fname}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to delete {fname}: {e}")

            st.markdown("---")



    def delete_album(self):
        conn = db.get_connection()
        cur = conn.cursor()

        # --- Select category ---
        cur.execute("SELECT id, name FROM photo_category ORDER BY name")
        categories = cur.fetchall()
        category_map = {name: cid for cid, name in categories}

        selected_category = st.selectbox(
            "Select Category",
            ["-- Select --"] + list(category_map.keys())
        )
        if selected_category == "-- Select --":
            st.info("Select a category to continue")
            return

        category_id = category_map[selected_category]

        # --- Select album created by current user ---
        cur.execute(
            "SELECT id, title FROM photo_album WHERE category_id=%s AND created_by=%s ORDER BY created_at",
            (category_id, self.username)
        )
        albums = cur.fetchall()
        if not albums:
            st.info("No albums created by you in this category")
            return

        album_map = {title: aid for aid, title in albums}
        selected_album = st.selectbox("Select Album to Delete", list(album_map.keys()))

        # --- Confirm delete ---
        if st.button(f"Delete Album '{selected_album}'", key=f"delete_album_{album_map[selected_album]}"):
            if st.confirm(f"Are you sure you want to delete album '{selected_album}'? This will delete all photos inside it."):
                try:
                    album_id = album_map[selected_album]

                    # Delete all photos in the album from filesystem and DB
                    cur.execute("SELECT file_path FROM photo WHERE album_id=%s", (album_id,))
                    photo_paths = [row[0] for row in cur.fetchall()]
                    for path in photo_paths:
                        if os.path.exists(path):
                            os.remove(path)

                    cur.execute("DELETE FROM photo WHERE album_id=%s", (album_id,))
                    cur.execute("DELETE FROM photo_album WHERE id=%s AND created_by=%s", (album_id, self.username))
                    conn.commit()

                    st.success(f"Album '{selected_album}' and its photos have been deleted ✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to delete album: {e}")



    def render_page(self):
        tab = st.radio(
            "Select action",
            ["📤 Upload Photos", "🖼️ View Gallery", "📂 Add/Rename Category", "🎞️ Transfer/Rename Album", "🗑 Delete My Photos"],
            horizontal=True
        )
        st.markdown("---")
        if tab == "📤 Upload Photos":
            self.render_upload_section()
        elif tab == "📂 Add/Rename Category":
            self.add_category()
        elif tab == "🎞️ Transfer/Rename Album":
            mode = st.radio("Select option", ['Rename', 'Transfer Album', 'Delete Album'], horizontal=True)
            if mode == "Rename":
                self.rename_album()
            elif mode == "Transfer Album":
                self.transfer_photo()
            else:
                self.delete_album()
        elif tab == "🗑 Delete My Photos":
            self.render_my_photos_section()
        else:
            self.render_gallery_section()


if __name__ == "__main__":
    Gallery().render_page()