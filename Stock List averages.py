import yfinance as yf
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import pandas as pd
from pandas.tseries.offsets import BDay  # Import Business Day offset for adjusting dates
import time


class StockVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Stock Price Visualizer")

        self.timeframe_options = ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max']
        self.selected_timeframe = tk.StringVar(value=self.timeframe_options[2])
        self.start_date = tk.StringVar(value="2020-01-01")  # Default start date
        self.end_date = tk.StringVar(value="2020-02-01")  # Default end date

        self.stock_list = []  # Empty initial stock list
        self.stock_percentages = {}  # Empty initial stock percentages
        self.starting_amount_entry = tk.StringVar(value="1000")  # Default starting amount

        self.create_main_widgets()
        self.canvas = None
        # Add stock_data attribute to store downloaded data
        self.stock_data = {}
        
    def create_main_widgets(self):
        # Timeframe selection
        tk.Label(self.root, text="Select Timeframe:").grid(row=0, column=0, sticky='w', padx=(5, 0), pady=5)
        timeframe_selector = ttk.Combobox(self.root, textvariable=self.selected_timeframe, values=self.timeframe_options, state="readonly")
        timeframe_selector.grid(row=0, column=1, sticky='w', padx=(0, 5), pady=5)
        timeframe_selector.bind("<<ComboboxSelected>>", self.plot_stock)

        # Start date entry
        tk.Label(self.root, text="Enter Start Date (YYYY-MM-DD):").grid(row=0, column=2, sticky='w', padx=5, pady=5)
        start_date_entry = tk.Entry(self.root, textvariable=self.start_date)
        start_date_entry.grid(row=0, column=3, sticky='w', padx=5, pady=5)

        # End date entry
        tk.Label(self.root, text="Enter End Date (YYYY-MM-DD) or 'now' for live time:").grid(row=0, column=4, sticky='w', padx=5, pady=5)
        end_date_entry = tk.Entry(self.root, textvariable=self.end_date)
        end_date_entry.grid(row=0, column=5, sticky='w', padx=5, pady=5)

        def set_current_date(event):
            if end_date_entry.get().lower() == "now":
                end_date_entry.delete(0, tk.END)  # Clear the current content
                end_date_entry.insert(0, pd.Timestamp.now().strftime("%Y-%m-%d"))

        # Bind the event to the entry
        end_date_entry.bind("<FocusOut>", set_current_date)

        # Starting amount entry
        tk.Label(self.root, text="Enter Starting Amount:").grid(row=0, column=6, sticky='w', padx=5, pady=5)
        starting_amount_entry = tk.Entry(self.root, textvariable=self.starting_amount_entry)  # Use textvariable here
        starting_amount_entry.grid(row=0, column=7, sticky='w', padx=5, pady=5)

        # Portfolio settings menu bar
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)
        portfolio_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Portfolio", menu=portfolio_menu)
        portfolio_menu.add_command(label="Portfolio Details", command=self.open_portfolio_details)

        # Frame for the plot
        self.graph_frame = tk.Frame(self.root)
        self.graph_frame.grid(row=1, column=0, columnspan=8, sticky='sew', padx=5, pady=5)
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.minsize(800, 400)  # Set a minimum window size

    def open_portfolio_details(self):
        # Create a top-level window for portfolio details
        details_window = tk.Toplevel()
        details_window.title('Portfolio Details')

        # Function to add stocks in the portfolio details window
        def add_stock():
            stock_symbol = simpledialog.askstring("Add Stock", "Enter the stock symbol:", parent=details_window)
            if stock_symbol:
                if stock_symbol not in self.stock_list:
                    # Prompt for entering the percentage
                    percentage_str = simpledialog.askstring("Enter Percentage", f"Enter the percentage for {stock_symbol}:", parent=details_window)
                    
                    try:
                        # Convert the percentage to a float
                        percentage = float(percentage_str)
                        if 0 <= percentage <= 100:
                            self.stock_list.append(stock_symbol)
                            self.stock_percentages[stock_symbol] = tk.DoubleVar(value=percentage)
                            redraw_stock_entries()
                            self.plot_stock()
                        else:
                            messagebox.showerror("Error", "Percentage must be between 0 and 100.")
                    except (ValueError, TypeError):
                        messagebox.showerror("Error", "Invalid percentage. Please enter a valid number.")
                else:
                    messagebox.showinfo("Info", f"Stock '{stock_symbol}' already in the portfolio.")

        # Function to remove stocks in the portfolio details window
        def remove_stock(stock_symbol):
            if stock_symbol in self.stock_list:
                self.stock_list.remove(stock_symbol)
                del self.stock_percentages[stock_symbol]
                redraw_stock_entries()
                self.plot_stock()

        
        # Function to redraw the stock entries
        def redraw_stock_entries():
            # Clear the current stock entries
            for widget in details_window.winfo_children():
                widget.destroy()

            # Add new stock entries
            for stock in self.stock_list:
                entry_frame = tk.Frame(details_window)
                entry_frame.pack(fill='x', padx=5, pady=5)

                # Stock Symbol and Percentage Entry
                tk.Label(entry_frame, text=f"{stock} (%):").pack(side="left")
                tk.Entry(entry_frame, textvariable=self.stock_percentages[stock]).pack(side="left")

                # Current Price on Start Date Entry (read-only)
                current_price_on_start_date_var = tk.StringVar(value="N/A")
                tk.Label(entry_frame, text="Start Date Price:").pack(side="left")
                tk.Entry(entry_frame, textvariable=current_price_on_start_date_var, state='readonly', width=10).pack(side="left")

                # Current Price Entry (read-only)
                current_price_var = tk.StringVar(value="N/A")
                tk.Label(entry_frame, text="Current Price:").pack(side="left")
                tk.Entry(entry_frame, textvariable=current_price_var, state='readonly', width=10).pack(side="left")

                # Percentage Gain/Loss Entry (read-only)
                percent_gain_loss_var = tk.StringVar(value="N/A")
                tk.Label(entry_frame, text="P/L%:").pack(side="left")
                tk.Entry(entry_frame, textvariable=percent_gain_loss_var, state='readonly', width=10).pack(side="left")

                # Remove Button
                tk.Button(entry_frame, text="Remove", command=lambda s=stock: remove_stock(s)).pack(side="right")

                # Calculate and update shares owned
                shares_owned_var = tk.StringVar(value="N/A")
                tk.Label(entry_frame, text="Shares Owned:").pack(side="left")
                tk.Entry(entry_frame, textvariable=shares_owned_var, state='readonly', width=10).pack(side="left")

                #return monitary
                monetary_return_var = tk.StringVar(value="N/A")
                tk.Label(entry_frame, text="Monetary Return:").pack(side="left")
                tk.Entry(entry_frame, textvariable=monetary_return_var, state='readonly', width=10).pack(side="left")



                # Calculate and update values
                try:
                    timeframe = self.selected_timeframe.get()
                    starting_amount = float(self.starting_amount_entry.get())  # Retrieve the starting amount
                    percentage_alloc = float(self.stock_percentages[stock].get())  # Retrieve the percentage allocation for the stock
                    data = yf.download(stock, start=self.start_date.get(), end=self.end_date.get(), progress=False)

                    if not data.empty:
                        start_date_price = data['Close'].iloc[0]
                        current_price = data['Close'].iloc[-1]

                        current_price_on_start_date_var.set(f"${start_date_price:.2f}")
                        current_price_var.set(f"${current_price:.2f}")

                        # Calculate and update shares owned
                        allocated_amount = starting_amount * (percentage_alloc / 100)
                        shares_owned = allocated_amount / start_date_price
                        shares_owned_var.set(f"{shares_owned:.2f}")

                        # Calculate monetary return
                        # Current value of shares owned - Amount originally invested
                        monetary_return = (shares_owned * current_price) - allocated_amount
                        sign = '+' if monetary_return >= 0 else ''
                        monetary_return_var.set(f"{sign}${monetary_return:.2f}")

                        # Calculate percentage gain/loss
                        percent_gain_loss = ((current_price / start_date_price) - 1) * 100
                        # Prepend + or - sign before the percentage
                        sign = '+' if percent_gain_loss >= 0 else ''
                        percent_gain_loss_var.set(f"{sign}{percent_gain_loss:.2f}%")
                except Exception as e:
                    messagebox.showerror("Error", f"An error occurred while fetching data for {stock}: {str(e)}")

            # Add button to add new stock
            tk.Button(details_window, text="Add New Stock", command=add_stock).pack()

        redraw_stock_entries()




    


    @staticmethod
    def plot_stock_validate_stock_symbol(stock_symbol):
        return validate_stock_symbol(stock_symbol)

    def plot_stock(self, event=None):
        if self.canvas:
            self.canvas.get_tk_widget().pack_forget()
            self.canvas.get_tk_widget().destroy()

        # Start a new figure instance
        fig, ax = plt.subplots(figsize=(10, 6))
        timeframe = self.selected_timeframe.get()

        # Initialize a flag to track if we have found any valid data
        valid_data_found = False

        # Iterate over all stock symbols and their respective percentage
        for stock_symbol, percentage in self.stock_percentages.items():
            stock_symbol = stock_symbol.strip()

            # Check if the percentage is greater than 0
            if percentage.get() > 0:
                try:
                    # Attempt to validate stock symbol
                    if not self.plot_stock_validate_stock_symbol(stock_symbol):
                        continue

                    # Wait until a percentage is given before downloading
                    if percentage.get() == 0:
                        print(f"Stock: {stock_symbol} - Not included (Percentage is 0)")
                        continue

                    # Attempt to download stock data
                    data = yf.download(stock_symbol, period=timeframe, progress=False)

                    # If data is not empty, process it
                    if not data.empty:
                        valid_data_found = True  # We've found valid data!

                        # Continue with the logic to process and plot data
                        adjusted_close = data['Close'] * (1 + percentage.get() / 100)
                        percentage_change = ((adjusted_close.iloc[-1] / adjusted_close.iloc[0]) - 1) * 100

                        # Your debugging prints...
                        print(f"Stock: {stock_symbol}")
                        print("Original Data:")
                        print(data.head())
                        print("Adjusted Close:")
                        print(adjusted_close.head())

                        # Add plot for adjusted close
                        ax.plot(data.index, adjusted_close, label=f"{stock_symbol} ({'+' if percentage.get() > 0 else ''}{percentage.get()}%)")

                except Exception as e:
                    print(f"An error occurred during data download for {stock_symbol}: {str(e)}. Skipping this stock.")

        # After the loop, check if no valid data was found and show a warning if so
        if not valid_data_found:
            messagebox.showwarning("Warning", "No valid data available for any stock.")

        # Draw a vertical line for the start date
        start_date_str = self.start_date.get()
        try:
            start_date = pd.to_datetime(start_date_str)
        except ValueError:
            messagebox.showerror("Error", "Invalid start date format. Please use YYYY-MM-DD.")
            return

        ax.axvline(x=start_date, color='red', linestyle='--', label='Start Date')

        ax.set_title("Portfolio Stocks Performance")
        ax.set_xlabel("Date")
        ax.set_ylabel("Adjusted Close (based on % allocation)")
        ax.legend()



        self.canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


    

def validate_stock_symbol(symbol):
        try:
            stock_info = yf.Ticker(symbol)
            stock_info.history(period='1d')  # You can adjust the period as needed
            return True
        except Exception as e:
            print(f"Validation failed for stock symbol {symbol}: {str(e)}")
            return False

if __name__ == "__main__":
    root = tk.Tk()
    app = StockVisualizer(root)
    root.mainloop()
