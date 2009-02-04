class MyModelsController < ApplicationController
  # GET /my_models
  # GET /my_models.xml
  def index
    @my_models = MyModel.find(:all)

    respond_to do |format|
      format.html # index.html.erb
      format.xml  { render :xml => @my_models }
    end
  end

  # GET /my_models/1
  # GET /my_models/1.xml
  def show
    @my_model = MyModel.find(params[:id])

    respond_to do |format|
      format.html # show.html.erb
      format.xml  { render :xml => @my_model }
    end
  end

  # GET /my_models/new
  # GET /my_models/new.xml
  def new
    @my_model = MyModel.new

    respond_to do |format|
      format.html # new.html.erb
      format.xml  { render :xml => @my_model }
    end
  end

  # GET /my_models/1/edit
  def edit
    @my_model = MyModel.find(params[:id])
  end

  # POST /my_models
  # POST /my_models.xml
  def create
    @my_model = MyModel.new(params[:my_model])

    respond_to do |format|
      if @my_model.save
        flash[:notice] = 'MyModel was successfully created.'
        format.html { redirect_to(@my_model) }
        format.xml  { render :xml => @my_model, :status => :created, :location => @my_model }
      else
        format.html { render :action => "new" }
        format.xml  { render :xml => @my_model.errors, :status => :unprocessable_entity }
      end
    end
  end

  # PUT /my_models/1
  # PUT /my_models/1.xml
  def update
    @my_model = MyModel.find(params[:id])

    respond_to do |format|
      if @my_model.update_attributes(params[:my_model])
        flash[:notice] = 'MyModel was successfully updated.'
        format.html { redirect_to(@my_model) }
        format.xml  { head :ok }
      else
        format.html { render :action => "edit" }
        format.xml  { render :xml => @my_model.errors, :status => :unprocessable_entity }
      end
    end
  end

  # DELETE /my_models/1
  # DELETE /my_models/1.xml
  def destroy
    @my_model = MyModel.find(params[:id])
    @my_model.destroy

    respond_to do |format|
      format.html { redirect_to(my_models_url) }
      format.xml  { head :ok }
    end
  end
end
