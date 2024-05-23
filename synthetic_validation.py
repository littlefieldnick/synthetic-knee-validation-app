import configparser

import os

import numpy as np
import pandas as pd
import param

from panel.theme import Native
import panel as pn

config = configparser.ConfigParser()
config.read("./config/config.ini")

pn.config.design = Native

def init_setup(config):
    cache_dir = config['CACHE-DIR']["cache"]
    img_dir = config["SYNTHETIC-DIR"]["root"]
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    if not os.path.isfile(os.path.join(cache_dir, "data_records.csv")):
        files = [os.path.join(img_dir, file) for file in os.listdir(img_dir)]
        data_records = pd.DataFrame(
            {
                "data_record": files,
                "keep": np.zeros(len(files)),
                "remove": np.zeros(len(files)),
                "unsure": np.zeros(len(files))
            }
        )

        data_records.to_csv(os.path.join(cache_dir, "data_records.csv"), index=False)

    else:
        data_records = pd.read_csv(os.path.join(cache_dir, "data_records.csv"))

    remaining_start = data_records[(data_records.keep == 0) & (data_records.remove == 0) & (data_records.unsure == 0)].index[0]

    return data_records, remaining_start

class ImageRecord(param.Parameterized):
    image_path = param.String()

    @param.depends("image_path")
    def display_image(self):
        return pn.pane.Image(self.image_path, width=400, height=400)

class SyntheticDataRecord(param.Parameterized):
    df = param.DataFrame()
    curr_idx = param.Integer()

    keep = param.Action(lambda x: x.param.trigger('keep'))
    remove = param.Action(lambda x: x.param.trigger('remove'))
    unsure = param.Action(lambda x: x.param.trigger('unsure'))
    save = param.Action(lambda x: x.param.trigger('save'))
    def determine_image_status(self, record):
        if record.keep == 1:
            return "<span style='color:green'>Keep</span>"
        elif record.remove == 1:
            return "<span style='color:red'>Remove</span>"
        elif record.unsure == 1:
            return "<span style='color:#ffba00'>Unsure</span>"

        return "Unassigned"

    @param.depends('keep',watch=True)
    def update_keep(self):
        df = self.df
        df.remove[self.curr_idx] = 0
        df.unsure[self.curr_idx] = 0

        df.keep[self.curr_idx] = 1
        self.df = df

    @param.depends('remove', watch=True)
    def update_remove(self):
        df = self.df
        df.keep[self.curr_idx] = 0
        df.unsure[self.curr_idx] = 0
        df.remove[self.curr_idx] = 1
        self.df = df

    @param.depends('unsure', watch=True)
    def update_unsure(self):
        df = self.df
        df.keep[self.curr_idx] = 0
        df.remove[self.curr_idx] = 0
        df.unsure[self.curr_idx] = 1
        self.df = df

    @param.depends('save', watch=True)
    def save_progress(self):
        self.df.to_csv(os.path.join(config['CACHE-DIR']["cache"], "data_records.csv"), index=False)

    @param.depends('df', "curr_idx")
    def view_df(self):
        if self.curr_idx < 2:
            return pn.pane.DataFrame(self.df.head(5), sizing_mode="stretch_width", max_height=200)
        if self.curr_idx + 2 == self.df.shape[0]:
            return pn.pane.DataFrame(self.df.tail(5), sizing_mode="stretch_width", max_height=200)
        return pn.pane.DataFrame(self.df.loc[self.curr_idx-2:self.curr_idx+2], sizing_mode="stretch_width", max_height=200)

    @param.depends("df", "curr_idx")
    def view_header(self):
        curr_record = self.df.iloc[self.curr_idx]
        return pn.pane.Markdown(f"""
            ## File Name: {curr_record.data_record}
            ### Status: {self.determine_image_status(curr_record)}
        """)

class ValidationDashboard(pn.viewable.Viewer):
    data_records: SyntheticDataRecord = param.ClassSelector(class_=SyntheticDataRecord)
    image_record: ImageRecord = param.ClassSelector(class_=ImageRecord)

    def __panel__(self):

        text_pane = self.data_records.view_header

        status_buttons = pn.Param(self.data_records.param, parameters=["keep", "remove", "unsure"],
                               widgets={
                                   "keep": {"type": pn.widgets.Button, "button_type": "success", "width":250},
                                   "remove": {"type": pn.widgets.Button, "button_type": "danger", "width":250},
                                   "unsure": {"type": pn.widgets.Button, "button_type": "warning", "width":250}
                               }, show_name=False,    default_layout=pn.Column,

                               )

        backward = pn.widgets.Button(name='\u25c0', width=50)
        def prev_image(event):
            self.data_records.curr_idx -= 1
            if self.data_records.curr_idx < 0:
                self.data_records.curr_idx = 0

            self.image_record.image_path = self.data_records.df.loc[self.data_records.curr_idx].data_record


        pn.bind(prev_image, backward, watch=True)
        forward = pn.widgets.Button(name='\u25b6', width=50)

        def next_image(event):
            self.data_records.curr_idx += 1
            self.image_record.image_path = self.data_records.df.loc[self.data_records.curr_idx].data_record

        pn.bind(next_image, forward, watch=True)

        save_button = pn.Param(self.data_records.param, parameters=["save"],
                                  widgets={
                                      "save": {"type": pn.widgets.Button, "name":"💾 Save", "width": 100},

                                  }, show_name=False

                                  )
        operations_row = pn.Row(backward, forward, save_button)

        columns = pn.Row(self.image_record.display_image, pn.Column(text_pane, status_buttons, operations_row))

        panel_template =  pn.template.FastListTemplate(
            title="Synthetic Image Validation", accent=config["PANEL"]["accent"],
            main=[columns, pn.Row(self.data_records.view_df)], theme_toggle=False)

        return panel_template


data, curr_index = init_setup(config)
syn_data = SyntheticDataRecord(df=data, curr_idx=curr_index)
img_data = ImageRecord(image_path=data.loc[curr_index].data_record)
ValidationDashboard(data_records=syn_data, image_record=img_data).servable()


