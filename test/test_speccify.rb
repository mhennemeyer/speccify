require File.dirname(__FILE__) + "/test_helper.rb"

describe "top level description block with one example" do
  
  before do
    @horst = "Horst"
  end
  
  it "example3" do
    @horst.should == "Horst"
  end

  describe "second level description block" do

    before do
      @inge = "Inge"
    end
    
    it "Inge should be here" do
      @inge.should == "Inge"
    end
    
    it "Horst should still be here" do
      @horst.should == "Horst"
    end

  end
end